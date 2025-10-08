# decrypt.py
# Use:
#   py decrypt.py        -> modo normal (silencioso)
#   py decrypt.py -debug -> modo debug (tabelas interativas; imprime final em MAIÚSCULAS, 3 linhas antes)

import os
import re
import sys
import time
import importlib.util
from collections import Counter, OrderedDict, defaultdict

# ---------------------------
# Parte A (decodificação) - mantém prints originais
# ---------------------------
ascii_dict = {
    "00100000": " ",
    "00100001": "!", "00100010": '"', "00100011": "#", "00100100": "$", "00100101": "%",
    "00100110": "&", "00100111": "'", "00101000": "(", "00101001": ")", "00101010": "*",
    "00101011": "+", "00101100": ",", "00101101": "-", "00101110": ".", "00101111": "/",
    "00110000": "0", "00110001": "1", "00110010": "2", "00110011": "3", "00110100": "4",
    "00110101": "5", "00110110": "6", "00110111": "7", "00111000": "8", "00111001": "9",
    "00111010": ":", "00111011": ";", "00111100": "<", "00111101": "=", "00111110": ">",
    "00111111": "?", "01000000": "@",
    "01000001": "A", "01000010": "B", "01000011": "C", "01000100": "D", "01000101": "E",
    "01000110": "F", "01000111": "G", "01001000": "H", "01001001": "I", "01001010": "J",
    "01001011": "K", "01001100": "L", "01001101": "M", "01001110": "N", "01001111": "O",
    "01010000": "P", "01010001": "Q", "01010010": "R", "01010011": "S", "01010100": "T",
    "01010101": "U", "01010110": "V", "01010111": "W", "01011000": "X", "01011001": "Y",
    "01011010": "Z",
    "01011011": "[", "01011100": "\\", "01011101": "]", "01011110": "^", "01011111": "_",
    "01100000": "`",
    "01100001": "a", "01100010": "b", "01100011": "c", "01100100": "d", "01100101": "e",
    "01100110": "f", "01100111": "g", "01101000": "h", "01101001": "i", "01101010": "j",
    "01101011": "k", "01101100": "l", "01101101": "m", "01101110": "n", "01101111": "o",
    "01110000": "p", "01110001": "q", "01110010": "r", "01110011": "s", "01110100": "t",
    "01110101": "u", "01110110": "v", "01110111": "w", "01111000": "x", "01111001": "y",
    "01111010": "z",
    "01111011": "{", "01111100": "|", "01111101": "}", "01111110": "~"
}

def barra_progresso(duracao=1, largura=20, prefix=""):
    etapas = max(1, largura)
    intervalo = duracao / etapas if etapas > 0 else 0
    for i in range(etapas + 1):
        porcentagem = int((i / etapas) * 100)
        barra = "█" * i + "-" * (largura - i)
        sys.stdout.write(f"\r{prefix} [{barra}] {porcentagem}%")
        sys.stdout.flush()
        time.sleep(intervalo)
    print()

def processar_encoded_file(path="encoded.txt"):
    try:
        print("1 - Lendo o arquivo encoded.txt...")
        barra_progresso()
        with open(path, "r", encoding="utf-8") as f:
            linhas = f.readlines()

        print("2 - Decodificando os valores de binário pra ASCII")
        barra_progresso()

        todas_linhas_8bits = [[p.zfill(8) for p in re.split(r'\s+', l.strip()) if p] for l in linhas]
        texto_decodificado_linhas = ["".join(ascii_dict.get(p, '?') for p in linha_bits) for linha_bits in todas_linhas_8bits]
        tokens = [t for linha in texto_decodificado_linhas for t in re.split(r'\s+', linha.strip()) if t]

        print("3 - Gerando arquivo encoded_message.txt...")
        barra_progresso()
        with open("encoded_message.txt", "w", encoding="utf-8") as f:
            for token in tokens:
                f.write(f"{token}\n")

        print("4 - Contando frequência e ordenando palavras...")
        barra_progresso()
        cont = Counter(tokens)
        tokens_ordenados = sorted(tokens, key=lambda x: (len(x), -cont[x], x.lower()))

        print("5 - Criando arquivo encoded_message_sorted.txt...")
        barra_progresso()
        with open("encoded_message_sorted.txt", "w", encoding="utf-8") as f:
            for token in tokens_ordenados:
                f.write(f"{token}\n")

        # 3 linhas em branco antes da Parte B
        print("6 - Processo finalizado com sucesso!\n\n\n")

    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo '{path}' não foi encontrado.")
    except Exception as e:
        print(f"⚠️ Ocorreu um erro no código A: {e}")

# ---------------------------
# Helpers comuns a B
# ---------------------------
def contar_ascii_21_7E(token: str) -> int:
    return sum(1 for c in token if 0x21 <= ord(c) <= 0x7E) if token else 0

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
    if not os.path.isfile(input_path):
        print(f"❌ ERRO: '{input_path}' não encontrado.", file=sys.stderr)
        return False
    try:
        with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
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

# ---------------------------
# Print helpers finais (modo normal)
# ---------------------------
def print_decifrado_corrido_duplo(filepath):
    if not os.path.isfile(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().replace("\r", " ").replace("\n", " ")
    # imprime corrido + duas linhas em branco
    sys.stdout.write(content + "\n\n")
    sys.stdout.flush()

def print_final_em_maiusculo(filepath):
    if not os.path.isfile(filepath):
        print("(encoded_DECIFRADO.txt não encontrado)")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().replace("\r", " ").replace("\n", " ")
    print("\n\nFinalizado com sucesso!!!\n\n")
    print(content.upper())

# ---------------------------
# small helper used by debug get attribution string
# (placed here so it's available when used)
# ---------------------------
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

# ---------------------------
# Modo silencioso (NÃO MODIFICAR)
# ---------------------------
def executar_codigo_b_silent():
    # remove previous snapshot if present
    if os.path.exists("encoded_DECIFRADO.txt"):
        try:
            os.remove("encoded_DECIFRADO.txt")
        except Exception:
            pass

    grupos, lengths_order = carregar_tokens_agrupados("encoded_message_sorted.txt")
    if not grupos:
        return
    dict1 = carregar_dict_de_arquivo("1word_counts.py", "word_counts_english_rank")
    dict2 = carregar_dict_de_arquivo("2top_words.py", "top_words_english_rank")

    mapa = OrderedDict()
    next_token_index = {l: 0 for l in lengths_order}
    token_candidate_pos = {}  # token -> pos
    exhausted_lengths = set()
    used_target_words = set()

    while not all(l in exhausted_lengths for l in lengths_order):
        nova_atribuicao = False
        for length in sorted(lengths_order):
            if length in exhausted_lengths:
                continue
            candidates = grupos.get(length, [])
            idx = next_token_index.get(length, 0)
            if idx >= len(candidates):
                exhausted_lengths.add(length)
                continue
            token = candidates[idx]
            pos = token_candidate_pos.get(token, 0)
            # buscar pos-ésimo candidato respeitando used_target_words
            cand = None
            idx_cand = 0
            for d in (dict1, dict2):
                for w in d.keys():
                    if w in used_target_words:
                        continue
                    if contar_ascii_21_7E(w) != length:
                        continue
                    if idx_cand == pos:
                        cand = w
                        break
                    idx_cand += 1
                if cand:
                    break
            if not cand:
                next_token_index[length] = idx + 1
                token_candidate_pos.pop(token, None)
                if next_token_index[length] >= len(candidates):
                    exhausted_lengths.add(length)
                continue

            conflict, _ = mapping_conflicts_bidirectional(token, cand, mapa)
            if conflict:
                token_candidate_pos[token] = pos + 1
                continue

            # ACEITO
            for s_ch, t_ch in zip(token, cand):
                if s_ch not in mapa:
                    mapa[s_ch] = t_ch
                    nova_atribuicao = True

            used_target_words.add(cand)
            token_candidate_pos.pop(token, None)
            next_token_index[length] = idx + 1
            if next_token_index[length] >= len(candidates):
                exhausted_lengths.add(length)

        if nova_atribuicao:
            aplicar_mapa_e_escrever_preservando_case("encoded_message.txt", "encoded_DECIFRADO.txt", mapa)
            print_decifrado_corrido_duplo("encoded_DECIFRADO.txt")
        else:
            # evitar busy loop
            time.sleep(0.01)

    # finalização
    aplicar_mapa_e_escrever_preservando_case("encoded_message.txt", "encoded_DECIFRADO.txt", mapa)
    print_final_em_maiusculo("encoded_DECIFRADO.txt")
    salvar_mapping_py("mapping.py", mapa)

# ---------------------------
# Função utilitária de tabela (para debug)
# ---------------------------
def print_table(rows, headers):
    cols = len(headers)
    col_widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            col_widths[i] = max(col_widths[i], len(str(r[i])))
    sep = " | "
    line_sep = "-+-".join("-" * w for w in col_widths)
    print()
    print(sep.join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
    print(line_sep)
    for r in rows:
        print(sep.join(str(r[i]).ljust(col_widths[i]) for i in range(cols)))
    print()

# ---------------------------
# Modo DEBUG: mantém tabelas originais, imprime tabela+snapshot+pause
# apenas quando a passada tiver nova atribuição; ao final pula 3 linhas e
# imprime todo o conteúdo corrido em MAIÚSCULAS.
# ---------------------------
def print_final_decifrado_debug(filepath):
    if not os.path.isfile(filepath):
        print("(encoded_DECIFRADO.txt não encontrado)")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().replace("\r", " ").replace("\n", " ")
    # pula 3 linhas antes e imprime tudo em maiúsculas em uma linha
    sys.stdout.write("\n\n\n" + content.upper() + "\n")
    sys.stdout.flush()

def executar_codigo_b_debug():
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
        progress_made = False
        rows = []

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
            cand = None
            idx_cand = 0
            for d in (dict1, dict2):
                for w in d.keys():
                    if w in used_target_words:
                        continue
                    if contar_ascii_21_7E(w) != length:
                        continue
                    if idx_cand == pos:
                        cand = w
                        break
                    idx_cand += 1
                if cand:
                    break

            fonte = None
            if cand:
                fonte = "1word_counts.py" if cand in dict1 else "2top_words.py"

            attempted_attribution = (build_attribution(token_to_try, cand) if cand else "-")

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

        # Somente imprimir tabela, snapshot e pausa se progress_made for True
        if progress_made:
            print(f"\n   Passada #{round_idx} sobre comprimentos...")
            headers = ["Compr.", "Token", "Candidate", "Fonte", "Resultado", "Detalhe", "Atribuição"]
            print_table(rows, headers)

            # grava snapshot parcial
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
        else:
            # sem progressos nesta passada -> não imprime nem pausa, continua imediatamente
            pass

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

    # salvar mapping.py
    py_path = "mapping.py"
    if salvar_mapping_py(py_path, mapa):
        print(f"8 - Mapa salvo em '{py_path}'.")
    else:
        print("⚠️ Falha ao salvar mapping.py.", file=sys.stderr)

    print("\n✔️ Processo COMPLETO (FINAL v6 com gravação incremental por passada).")

    # --- AQUI: imprimir a mensagem final pedida (modo debug) ---
    print_final_decifrado_debug("encoded_DECIFRADO.txt")

# ---------------------------
# Entrypoint
# ---------------------------
def main():
    debug = any(a in ("-debug", "--debug") for a in sys.argv[1:])
    print(">>> Iniciando pipeline: Código A (decodificação) -> Código B (mapeamento)")
    processar_encoded_file("encoded.txt")
    if debug:
        print(">>> MODO DEBUG: imprimirá apenas passadas que aceitarem ao menos 1 nova atribuição.")
        executar_codigo_b_debug()
    else:
        print(">>> MODO NORMAL: execução silenciosa (aplica mapeamentos e imprime somente quando há nova atribuição).")
        executar_codigo_b_silent()

if __name__ == "__main__":
    main()
