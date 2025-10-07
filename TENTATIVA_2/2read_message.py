import os
import ast
from top_words import english_rank  # dicionário: palavra -> rank (1 = mais frequente)

# ---------- utilitários ----------
def match_percent(a: str, b: str) -> float:
    """Percentual de caracteres iguais na mesma posição entre duas palavras do mesmo tamanho."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    matches = sum(1 for ch1, ch2 in zip(a, b) if ch1 == ch2)
    return (matches / len(a)) * 100.0

def criar_copia_se_nao_existir():
    """Cria 'message_NEW.txt' a partir de 'message.txt' caso não exista."""
    if not os.path.exists("message_NEW.txt"):
        if os.path.exists("message.txt"):
            with open("message.txt", "r", encoding="utf-8") as original:
                conteudo = original.read()
            with open("message_NEW.txt", "w", encoding="utf-8") as copia:
                copia.write(conteudo)
            print("⚙️  'message_NEW.txt' não existia e foi criado a partir de 'message.txt'.")
        else:
            print("❌ Nenhum arquivo encontrado: nem 'message_NEW.txt' nem 'message.txt'.")
            return False
    return True

def _freq_aceitavel(original: str, candidato: str) -> bool:
    """
    Retorna False se o candidato tem alguma letra (que já existe na original)
    com frequência maior do que essa letra na palavra original.
    Letras novas são permitidas.
    """
    original_upper = original.upper()
    candidato_upper = candidato.upper()
    letras_comuns = set(original_upper) & set(candidato_upper)
    for ch in letras_comuns:
        if candidato_upper.count(ch) > original_upper.count(ch):
            return False
    return True

def _read_lines_preserve(filepath: str):
    """Lê linhas mantendo o número de linhas (retorna [] se o arquivo não existir)."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [linha.rstrip("\n") for linha in f.readlines()]

def _write_lines(filepath: str, lines):
    """Escreve lista de linhas (cada item sem '\\n') no arquivo."""
    with open(filepath, "w", encoding="utf-8") as f:
        for linha in lines:
            f.write((linha if linha is not None else "") + "\n")

# ---------- carregar / salvar dicionários ----------
def _carregar_update_map_existente(filepath="update_dictionary.py"):
    """Carrega update_map de update_dictionary.py usando ast.literal_eval seguro; retorna dict[str,str]."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            texto = f.read()
        idx = texto.find("update_map")
        if idx == -1:
            return {}
        eq_index = texto.find("=", idx)
        if eq_index == -1:
            return {}
        rhs = texto[eq_index + 1:].strip()
        try:
            loaded = ast.literal_eval(rhs)
            if isinstance(loaded, dict):
                return {str(k): str(v) for k, v in loaded.items()}
            return {}
        except Exception:
            # isolar primeiro dict e tentar avaliar
            start = rhs.find("{")
            if start == -1:
                return {}
            depth = 0
            end = None
            for i, ch in enumerate(rhs[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end is None:
                return {}
            snippet = rhs[start:end+1]
            try:
                loaded = ast.literal_eval(snippet)
                if isinstance(loaded, dict):
                    return {str(k): str(v) for k, v in loaded.items()}
                return {}
            except Exception:
                return {}
    except Exception:
        return {}

def _salvar_update_map(mapa: dict, filepath="update_dictionary.py"):
    """Salva o mapa consolidado em update_dictionary.py (uma entrada por linha)."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write("# Dicionário consolidado gerado por comparar_e_atualizar()\n\n")
            f.write("update_map = {\n")
            for k in sorted(mapa.keys()):
                v = mapa[k]
                f.write(f"    {repr(k)}: {repr(v)},\n")
            f.write("}\n")
        print(f"\n📘 Dicionário consolidado salvo/atualizado em '{filepath}'.")
    except Exception as e:
        print(f"❌ Erro ao salvar '{filepath}': {e}")

def _salvar_update_changes(mapa: dict, filepath="update_dictionary_changes.py"):
    """Salva apenas o delta (as mudanças desta execução). Se vazio, não cria arquivo."""
    if not mapa:
        print("\nℹ️ Nenhuma alteração para salvar em 'update_dictionary_changes.py'.")
        return
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write("# Dicionário com APENAS as alterações desta execução\n\n")
            f.write("update_map = {\n")
            for k in sorted(mapa.keys()):
                v = mapa[k]
                f.write(f"    {repr(k)}: {repr(v)},\n")
            f.write("}\n")
        print(f"\n📘 Arquivo apenas-com-alterações salvo em '{filepath}'.")
    except Exception as e:
        print(f"❌ Erro ao salvar '{filepath}': {e}")

# ---------- função principal ----------
def comparar_e_atualizar(arquivo_path="message_NEW.txt", final_path="message_NEW_FINAL.txt"):
    if not criar_copia_se_nao_existir():
        return

    # lê linhas (preservando número de linhas)
    palavras_arquivo = _read_lines_preserve(arquivo_path)
    total_linhas = len(palavras_arquivo)

    atualizadas = list(palavras_arquivo)  # será atualizada (linhas ficam vazias onde ocorreu match)
    alteracoes = []  # lista de tuplas: (linha(1-based), original, candidato_escolhido, match%, rank_value)

    # processa cada linha
    for i, palavra_original in enumerate(palavras_arquivo, start=1):
        if not palavra_original or palavra_original.strip() == "":
            continue  # pula linhas já vazias

        palavra = palavra_original.upper()
        tamanho = len(palavra)

        candidatos = [p for p in english_rank.keys() if len(p) == tamanho]

        melhores = []
        for cand in candidatos:
            if not _freq_aceitavel(palavra, cand):
                continue
            pcent = match_percent(palavra, cand)
            # <<< comparação estrita: maior que 50%, NÃO aceita igual a 50% >>>
            if pcent > 50 and pcent < 100:
                rank_value = english_rank.get(cand, 9999)
                melhores.append((cand, pcent, rank_value))

        if melhores:
            # escolhe pelo menor rank_value (mais frequente), e em empate, maior match% via key
            melhor = min(melhores, key=lambda x: (x[2], -x[1]))
            cand, pcent, rank_value = melhor
            alteracoes.append((i, palavra_original, cand, pcent, rank_value))
            atualizadas[i-1] = ""  # remove a palavra desta linha em message_NEW.txt
        else:
            # sem alterações
            pass

    # reescreve message_NEW.txt (linhas vazias onde houve match)
    _write_lines(arquivo_path, atualizadas)
    print(f"\n💾 '{arquivo_path}' atualizado (linhas correspondentes removidas onde houve match).")

    # prepara/atualiza message_NEW_FINAL.txt (garantindo pelo menos same número de linhas)
    final_lines = _read_lines_preserve(final_path)
    if len(final_lines) < total_linhas:
        final_lines.extend([""] * (total_linhas - len(final_lines)))

    moved_report = []
    for linha_num, original, novo, pcent, rank_value in alteracoes:
        final_lines[linha_num - 1] = novo
        moved_report.append((linha_num, original, novo, pcent, rank_value))

    _write_lines(final_path, final_lines)
    if moved_report:
        print(f"\n💾 '{final_path}' atualizado (palavras movidas para as linhas correspondentes).")
        print("\n🔄 Movimentações realizadas:")
        for linha_num, original, novo, pcent, rank_value in moved_report:
            print(f"  linha {linha_num}: '{original}' → '{novo}'  (match: {pcent:.1f}%, rank: {rank_value})")
    else:
        print("\nℹ️ Nenhuma palavra foi movida para o arquivo final (nenhuma alteração).")

    # -------------------------
    # gerar mapeamento apenas com as letras modificadas nesta execução
    # resolve conflitos preferindo sugestão vinda da palavra candidata com melhor rank (rank_value menor).
    _temp_map = {}   # ch1 -> (ch2, rank_value, source_candidate_word, source_original_word, line)
    for linha_num, original, novo, pcent, rank_value in alteracoes:
        orig_up = original.upper()
        novo_up = novo.upper()
        for ch1, ch2 in zip(orig_up, novo_up):
            if ch1 == ch2:
                continue
            if ch1 not in _temp_map:
                _temp_map[ch1] = (ch2, rank_value, novo, original, linha_num)
            else:
                existing_ch2, existing_rank, existing_src_cand, existing_src_orig, existing_line = _temp_map[ch1]
                # preferir menor rank_value (mais frequente)
                if rank_value < existing_rank:
                    _temp_map[ch1] = (ch2, rank_value, novo, original, linha_num)
                # se empate de rank_value, mantemos a primeira ocorrência (não altera)
                # se rank_value > existing_rank, mantém a existente

    # converte para formato simples ch1->ch2 (somente mudanças desta execução)
    novo_mapeamento = {k: v for k, (v, *_rest) in _temp_map.items()}

    # salva delta (apenas mudanças desta execução)
    _salvar_update_changes(novo_mapeamento, "update_dictionary_changes.py")

    # mescla com consolidado existente e salva consolidado
    if novo_mapeamento:
        existente = _carregar_update_map_existente("update_dictionary.py")

        adicionadas = []
        sobrescritas = []
        mantidas = []

        for k, v in novo_mapeamento.items():
            if k not in existente:
                adicionadas.append((k, v))
            else:
                if existente[k] != v:
                    sobrescritas.append((k, existente[k], v))
                else:
                    mantidas.append((k, v))

        existentes_sem_novas = [(k, existente[k]) for k in sorted(existente.keys()) if k not in novo_mapeamento]

        # sobrescreve apenas com as novas alterações selecionadas
        existente.update(novo_mapeamento)
        _salvar_update_map(existente, "update_dictionary.py")

        # --- RELATÓRIO resumido sobre o que foi atualizado no dicionário ---
        print("\n📊 Relatório de atualizações do dicionário (consolidado):")
        if adicionadas:
            print("  ➕ Adicionadas:")
            for k, v in sorted(adicionadas):
                print(f"     {k} → {v}")
        if sobrescritas:
            print("  ✏️ Sobrescritas:")
            for k, old, new in sorted(sobrescritas):
                print(f"     {k}: {old} → {new}")
        if mantidas:
            print("  ✅ Já existentes e iguais nas novas entradas:")
            for k, v in sorted(mantidas):
                print(f"     {k} → {v}")
        if existentes_sem_novas:
            print("  🗂️ Entradas antigas preservadas (sem modificação):")
            for k, v in existentes_sem_novas:
                print(f"     {k} → {v}")
    else:
        print("\nℹ️ Nenhum mapeamento de letras foi gerado (nenhuma substituição parcial encontrada).")

# ---------- execução ----------
if __name__ == "__main__":
    comparar_e_atualizar()
