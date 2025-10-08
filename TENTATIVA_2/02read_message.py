# build_and_apply_mapping_final_v6_table_incremental.py
"""
Versão FINAL v6:
- Mesmas regras da FINAL v5 (uma tentativa por comprimento por passada, candidato por token,
  checagem bidirecional, não reutilizar alvos, pausa por passada, tabela por passada).
- NOVO: após cada passada, grava **encoded_DECIFRADO.txt** aplicando o mapa parcial atual,
  permitindo inspecionar a decifração incrementalmente.
- Salva somente mapping.py no final (dicionário Python).
"""

import os
import sys
import time
import importlib.util
from collections import OrderedDict, defaultdict

# -----------------------
# Utils
# -----------------------
def barra_progresso(duracao=0.3, largura=20, prefix=""):
    etapas = largura
    intervalo = duracao / etapas if etapas > 0 else 0
    for i in range(etapas + 1):
        porcentagem = int((i / etapas) * 100) if etapas else 100
        barra = "█" * i + "-" * (largura - i)
        sys.stdout.write(f"\r{prefix} [{barra}] {porcentagem}%")
        sys.stdout.flush()
        time.sleep(intervalo)
    print()

def contar_ascii_21_7E(token: str) -> int:
    if token is None:
        return 0
    return sum(1 for c in token if 0x21 <= ord(c) <= 0x7E)

def carregar_dict_de_arquivo(filepath, varname):
    if not os.path.isfile(filepath):
        return OrderedDict()
    try:
        spec = importlib.util.spec_from_file_location("mod_tmp_" + os.path.basename(filepath), filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        obj = getattr(mod, varname, {})
        if isinstance(obj, dict):
            return OrderedDict(obj)
        else:
            print(f"⚠️ Aviso: variável '{varname}' em '{filepath}' não é dict. Ignorando.")
            return OrderedDict()
    except Exception as e:
        print(f"⚠️ Erro ao carregar '{filepath}': {e}", file=sys.stderr)
        return OrderedDict()

def carregar_tokens_agrupados(sorted_path="encoded_message_sorted.txt"):
    if not os.path.isfile(sorted_path):
        print(f"❌ ERRO: '{sorted_path}' não encontrado.", file=sys.stderr)
        return {}, []
    tokens = []
    seen = set()
    with open(sorted_path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.rstrip("\n\r")
            if t is None:
                continue
            t = t.strip()
            if t == "":
                continue
            if t in seen:
                continue
            seen.add(t)
            tokens.append(t)
    grupos = defaultdict(list)
    lengths_order = []
    for t in tokens:
        c = contar_ascii_21_7E(t)
        if c not in grupos:
            lengths_order.append(c)
        grupos[c].append(t)
    lengths_order = sorted(set(lengths_order))
    return grupos, lengths_order

def mapping_conflicts_bidirectional(src_token, tgt_token, current_map):
    rev = {v: k for k, v in current_map.items()}
    for i, s_ch in enumerate(src_token):
        t_ch = tgt_token[i]
        if s_ch in current_map and current_map[s_ch] != t_ch:
            return True, ("origin_mapped", s_ch, current_map[s_ch], t_ch)
        if t_ch in rev:
            existing_src = rev[t_ch]
            if existing_src != s_ch:
                return True, ("target_taken", t_ch, existing_src, s_ch)
    return False, None

def aplicar_mapa_e_escrever_preservando_case(input_path, output_path, mapa):
    """
    Aplica mapa char->char sobre o arquivo inteiro.
    Quando um caractere c é substituído (c in mapa), escreve mapa[c].lower().
    Caso contrário, escreve c exatamente como no original.
    """
    if not os.path.isfile(input_path):
        print(f"❌ ERRO: '{input_path}' não encontrado.", file=sys.stderr)
        return False
    try:
        with open(input_path, "r", encoding="utf-8") as fin, \
             open(output_path, "w", encoding="utf-8") as fout:
            for line in fin:
                out_chars = []
                for c in line:
                    if c in mapa:
                        out_chars.append(str(mapa[c]).lower())
                    else:
                        out_chars.append(c)
                fout.write("".join(out_chars))
        return True
    except Exception as e:
        print(f"⚠️ Erro ao gravar '{output_path}': {e}", file=sys.stderr)
        return False

def contar_ocorrencias_por_origem(path, mapa):
    counts = {}
    if not os.path.isfile(path) or not mapa:
        return counts
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            for c in line:
                if c in mapa:
                    counts[c] = counts.get(c, 0) + 1
    return counts

def salvar_mapping_py(path, mapa, varname="mapping"):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Auto-gerado: mapa de substituição (origem -> alvo)\n{varname} = {{\n")
            for k, v in mapa.items():
                k_esc = k.replace("'", "\\'")
                v_esc = v.replace("'", "\\'")
                f.write(f"    '{k_esc}': '{v_esc}',\n")
            f.write("}\n")
        return True
    except Exception as e:
        print(f"⚠️ Falha ao salvar {path}: {e}", file=sys.stderr)
        return False

# -----------------------
# Candidate fetching across dict1 then dict2 respecting skip_targets and position index
# -----------------------
def get_candidate_by_pos(count, dict1, dict2, skip_targets, pos):
    """
    Retorna o pos-ésimo candidato (0-based) entre dict1 keys então dict2 keys
    que tenham comprimento count (pela regra ASCII) e não estejam em skip_targets.
    """
    if pos < 0:
        return None, None
    idx = 0
    for d in (dict1, dict2):
        for w in d.keys():
            if w in skip_targets:
                continue
            if contar_ascii_21_7E(w) != count:
                continue
            if idx == pos:
                return w, d.get(w)
            idx += 1
    return None, None

# -----------------------
# Pretty table printer (simple, no deps)
# -----------------------
def print_table(rows, headers):
    cols = len(headers)
    col_widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            col_widths[i] = max(col_widths[i], len(str(r[i])))

    sep = " | "
    line_sep = "-+-".join("-" * w for w in col_widths)

    header_line = sep.join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print()
    print(header_line)
    print(line_sep)

    for r in rows:
        print(sep.join(str(r[i]).ljust(col_widths[i]) for i in range(cols)))
    print()

# -----------------------
# Helper: build attribution string 'A->B, C->D'
# -----------------------
def build_attribution(src_token, tgt_token):
    if not src_token or not tgt_token:
        return "-"
    pairs = []
    for i, s in enumerate(src_token):
        try:
            t = tgt_token[i]
        except Exception:
            t = "?"
        pairs.append(f"{s}->{t}")
    return ", ".join(pairs)

# -----------------------
# Main
# -----------------------
def main():
    print("1 - Carregando tokens de 'encoded_message_sorted.txt' ...")
    barra_progresso(duracao=0.3, prefix="   etapa 1")
    grupos, lengths_order = carregar_tokens_agrupados("encoded_message_sorted.txt")
    if not grupos:
        print("❌ Nenhum token encontrado em 'encoded_message_sorted.txt' ou arquivo ausente. Abortando.")
        return
    print(f"   Grupos de comprimentos encontrados: {sorted(lengths_order)}")
    total_tokens = sum(len(v) for v in grupos.values())
    print(f"   Tokens únicos carregados: {total_tokens}")

    print("\n2 - Carregando dicionário 1word_counts.py -> word_counts_english_rank")
    barra_progresso(duracao=0.2, prefix="   etapa 2")
    dict1 = carregar_dict_de_arquivo("1word_counts.py", "word_counts_english_rank")
    print(f"   Itens carregados (1): {len(dict1)}")

    print("\n3 - Carregando dicionário 2top_words.py -> top_words_english_rank")
    barra_progresso(duracao=0.2, prefix="   etapa 3")
    dict2 = carregar_dict_de_arquivo("2top_words.py", "top_words_english_rank")
    print(f"   Itens carregados (2): {len(dict2)}")

    # estado
    mapa = OrderedDict()
    next_token_index = {length: 0 for length in lengths_order}
    token_candidate_pos = {}  # token -> int
    exhausted_lengths = set()
    used_target_words = set()

    print("\n4 - Construindo mapa incremental (uma tentativa por comprimento por passada, mantendo candidato por token)...")
    round_idx = 0
    # continuar até todos os comprimentos esgotados
    while not all(length in exhausted_lengths for length in lengths_order):
        round_idx += 1
        print(f"\n   Passada #{round_idx} sobre comprimentos...")
        progress_made = False

        rows = []  # tabela desta passada

        for length in sorted(lengths_order):
            if length in exhausted_lengths:
                continue

            candidates = grupos.get(length, [])
            idx = next_token_index.get(length, 0)

            if idx >= len(candidates):
                exhausted_lengths.add(length)
                rows.append((length, "-", "-", "-", "ESGOTADO", "nenhuma palavra restante", "-"))
                continue

            token_to_try = candidates[idx]
            pos = token_candidate_pos.get(token_to_try, 0)

            # buscar pos-ésimo candidato respeitando used_target_words
            cand, rank_raw = get_candidate_by_pos(length, dict1, dict2, used_target_words, pos)
            fonte = None
            if cand:
                fonte = "1word_counts.py" if cand in dict1 else "2top_words.py"

            # attribution only meaningful on ACEITO; here prepare but we'll only show if accepted
            attempted_attribution = build_attribution(token_to_try, cand) if cand else "-"

            if not cand:
                detail = "todos candidatos usados/esgotados"
                rows.append((length, token_to_try, "-", "-", "SEM CANDIDATO", detail, "-"))
                next_token_index[length] = idx + 1
                token_candidate_pos.pop(token_to_try, None)
                if next_token_index[length] >= len(candidates):
                    exhausted_lengths.add(length)
                    rows.append((length, "-", "-", "-", "ESGOTADO", "após avanço", "-"))
                continue

            conflict, detail = mapping_conflicts_bidirectional(token_to_try, cand, mapa)
            if conflict:
                if detail[0] == "origin_mapped":
                    _, s_ch, existing_target, attempted_target = detail
                    reason = f"orig {s_ch!r} já-> {existing_target!r}, tentaria {attempted_target!r}"
                else:
                    _, t_ch, existing_src, attempted_src = detail
                    reason = f"alvo {t_ch!r} já ocupado por {existing_src!r}, tentaria origem {attempted_src!r}"
                rows.append((length, token_to_try, cand, fonte, "REJEITADO", reason, "-"))
                token_candidate_pos[token_to_try] = pos + 1
                continue

            # ACEITO
            added = 0
            for i, s_ch in enumerate(token_to_try):
                t_ch = cand[i]
                if s_ch in mapa:
                    continue
                mapa[s_ch] = t_ch
                added += 1

            used_target_words.add(cand)
            token_candidate_pos.pop(token_to_try, None)
            next_token_index[length] = idx + 1

            result_detail = f"Pares adicionados: {added} (alvo '{cand}' marcado usado)"
            attribution = build_attribution(token_to_try, cand)
            rows.append((length, token_to_try, cand, fonte, "ACEITO", result_detail, attribution))

            if next_token_index[length] >= len(candidates):
                exhausted_lengths.add(length)
                rows.append((length, "-", "-", "-", "ESGOTADO", "após aceitação", "-"))

            progress_made = True
            # segue para próximo comprimento

        # imprimir tabela desta passada (com coluna 'Atribuição' mostrada somente em ACEITO)
        headers = ["Compr.", "Token", "Candidate", "Fonte", "Resultado", "Detalhe", "Atribuição"]
        print_table(rows, headers)

        # --- NOVO: gravar encoded_DECIFRADO.txt com o mapa parcial atual ---
        print("   Gravando snapshot parcial em 'encoded_DECIFRADO.txt' com o mapa atual...")
        if aplicar_mapa_e_escrever_preservando_case("encoded_message.txt", "encoded_DECIFRADO.txt", mapa):
            print("   → arquivo 'encoded_DECIFRADO.txt' atualizado (parcial).")
        else:
            print("   → falha ao atualizar 'encoded_DECIFRADO.txt' (ver mensagens de erro).")

        if not progress_made:
            print("\n   Passada terminou sem aceitar novos candidatos (mas indices/candidate_pos podem ter avançado).")
        else:
            print("\n   Passada terminou com pelo menos uma aceitação.")

        # pausa interativa se ainda houver comprimentos não esgotados
        if not all(length in exhausted_lengths for length in lengths_order):
            try:
                input("\n   Pressione Enter para continuar para a próxima passada (ou Ctrl+C para sair)...")
            except KeyboardInterrupt:
                print("\n   Interrompido pelo usuário. Saindo.")
                return

    # resumo do mapa
    print("\n5 - Mapa final construído:")
    if not mapa:
        print("   (vazio) nenhum mapeamento possível.")
    else:
        print(f"   Pares no mapa: {len(mapa)}")
        shown = 0
        for k, v in mapa.items():
            print(f"     {k!r} -> {v!r}")
            shown += 1
            if shown >= 200:
                break

    # relatório de ocorrências previstas
    print("\n6 - Contando ocorrências previstas no original...")
    barra_progresso(duracao=0.3, prefix="   etapa 6")
    occ = contar_ocorrencias_por_origem("encoded_message.txt", mapa)
    total_subs = sum(occ.values()) if occ else 0
    print(f"   Substituições previstas (soma de todas as origens): {total_subs}")
    if occ:
        for k, v in occ.items():
            print(f"     {k!r}: {v}")

    # última gravação final (garante estado final)
    print("\n7 - Gravando resultado final em 'encoded_DECIFRADO.txt' ...")
    if aplicar_mapa_e_escrever_preservando_case("encoded_message.txt", "encoded_DECIFRADO.txt", mapa):
        print("   → arquivo 'encoded_DECIFRADO.txt' gravado (final).")
    else:
        print("   → falha ao gravar 'encoded_DECIFRADO.txt' final.", file=sys.stderr)

    # salvar somente mapping.py conforme pedido
    py_path = "mapping.py"
    if salvar_mapping_py(py_path, mapa):
        print(f"8 - Mapa salvo em '{py_path}'.")
    else:
        print("⚠️ Falha ao salvar mapping.py.", file=sys.stderr)

    print("\n✔️ Processo COMPLETO (FINAL v6 com gravação incremental por passada).")

if __name__ == "__main__":
    main()
