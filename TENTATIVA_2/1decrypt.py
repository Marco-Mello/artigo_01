import re
from collections import Counter

# ===============================
# DICIONÁRIOS (mantidos integralmente)
# ===============================
ascii_dict = {
    "00100000": " ",  # espaço
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

frequencia_letras = {
    "E": 12.49, "T": 9.28, "A": 8.04, "O": 7.64, "I": 7.57, "N": 7.23,
    "S": 6.51, "R": 6.28, "H": 5.05, "L": 4.07, "D": 3.82, "C": 3.34,
    "U": 2.73, "M": 2.51, "F": 2.40, "P": 2.14, "G": 1.87, "W": 1.68,
    "Y": 1.66, "B": 1.48, "V": 1.05, "K": 0.54, "X": 0.23, "J": 0.16,
    "Q": 0.12, "Z": 0.09
}

frequencia_palavras = {
    "THE": 7.14, "OF": 4.16, "AND": 3.04, "TO": 2.60, "IN": 2.27, "A": 2.06,
    "IS": 1.13, "THAT": 1.08, "FOR": 0.88, "IT": 0.77, "AS": 0.77, "WAS": 0.74,
    "WITH": 0.70, "BE": 0.65, "BY": 0.63, "ON": 0.62, "NOT": 0.61, "HE": 0.55,
    "I": 0.52, "THIS": 0.51, "ARE": 0.50, "OR": 0.49, "HIS": 0.49, "FROM": 0.47,
    "AT": 0.46, "WHICH": 0.42, "BUT": 0.38, "HAVE": 0.37, "AN": 0.37, "HAD": 0.35,
    "THEY": 0.33, "YOU": 0.31, "WERE": 0.31, "THEIR": 0.29, "ONE": 0.29, "ALL": 0.28,
    "WE": 0.28, "CAN": 0.22, "HER": 0.22, "HAS": 0.22, "THERE": 0.22, "BEEN": 0.22,
    "IF": 0.21, "MORE": 0.21, "WHEN": 0.20, "WILL": 0.20, "WOULD": 0.20,
    "WHO": 0.20, "SO": 0.19, "NO": 0.19
}

# ===============================
# Função auxiliar: imprimir etapa
# ===============================
def etapa(numero, descricao):
    print(f"\n🔹 Etapa {numero}: {descricao}")
    input("👉 Pressione ENTER para continuar...\n")

# ===============================
# Função: imprime ranking completo A→Z
# ===============================
def imprimir_ranking_letras(texto_decodificado_linhas):
    etapa("7", "Calcular e exibir o ranking de letras (A→Z)")
    texto_total = "".join(texto_decodificado_linhas).upper()
    letras_somente = [c for c in texto_total if 'A' <= c <= 'Z']
    contagem = Counter(letras_somente)
    total_letras = sum(contagem.values())
    all_letters = [chr(c) for c in range(ord('A'), ord('Z')+1)]
    ranking_sorted = sorted(
        [(L, contagem.get(L, 0), contagem.get(L, 0)/total_letras*100 if total_letras else 0.0) for L in all_letters],
        key=lambda x: (-x[1], x[0])
    )
    print("\n🔠 RANKING COMPLETO DE LETRAS (mais frequentes → menos):\n")
    for pos, (letra, qtd, perc) in enumerate(ranking_sorted, start=1):
        print(f"{pos:02d}. {letra} -> {qtd} vezes ({perc:.2f}%)")
    print(f"\n📊 Total de letras contadas: {total_letras}\n")
    return [letra for letra, _, _ in ranking_sorted]

# ===============================
# Função: substituição final por frequência e salvamento do dicionário update_map
# ===============================
def substituir_por_frequencia_final(texto_decodificado_linhas, ranking_real):
    etapa("8", "Executar a substituição final baseada no ranking de frequência e salvar o dicionário de mapeamento")
    ranking_ref = [k for k, _ in sorted(frequencia_letras.items(), key=lambda x: x[1], reverse=True)]
    update_map = {ranking_real[i]: ranking_ref[i] for i in range(len(ranking_ref))}

    print("\n🔄 MAPEAMENTO FINAL DE SUBSTITUIÇÃO (texto → referência):")
    for k in sorted(update_map.keys()):
        print(f"   {k} → {update_map[k]}")

    # salvar update_map no arquivo update_dictionary.py
    try:
        with open("update_dictionary.py", "w", encoding="utf-8") as f:
            f.write("# Dicionário de substituição final (texto → referência)\n")
            f.write("update_map = {\n")
            for k, v in sorted(update_map.items()):
                f.write(f"    '{k}': '{v}',\n")
            f.write("}\n")
        print("\n✅ Dicionário de substituição salvo em 'update_dictionary.py'\n")
    except Exception as e:
        print(f"⚠️ Erro ao salvar 'update_dictionary.py': {e}")

    texto_transformado = []
    for linha in texto_decodificado_linhas:
        nova = ""
        for ch in linha:
            if ch.isalpha():
                up = ch.upper()
                mapped = update_map.get(up, up)
                nova += mapped.lower() if ch.islower() else mapped
            else:
                nova += ch
        texto_transformado.append(nova)

    print("✅ Texto transformado pela SUBSTITUIÇÃO FINAL.\n")
    return texto_transformado

# ===============================
# Função: separa e salva palavras (usando texto_transformado)
# ===============================
def salvar_e_imprimir_words_per_line(texto_transformado, output_filename="message.txt"):
    etapa("9", "Separar cada palavra do texto transformado por linha e salvar em 'message.txt'")
    tokens = []
    for linha in texto_transformado:
        tokens.extend([t for t in re.split(r'\s+', linha.strip()) if t != ""])
    print(f"\n📄 Total de palavras encontradas: {len(tokens)}\n")
    for i, token in enumerate(tokens, start=1):
        print(f"{i:03d}: {token}")
    try:
        with open(output_filename, "w", encoding="utf-8") as out:
            for token in tokens:
                out.write(f"{token}\n")
        print(f"\n✅ Palavras salvas em: {output_filename}\n")
    except Exception as e:
        print(f"⚠️ Erro ao salvar '{output_filename}': {e}")
    return tokens

# ===============================
# Função principal
# ===============================
def processar_encoded_file(path="encoded.txt"):
    print("📂 Iniciando processo interativo completo...\n")
    etapa("1", "Iniciar o processo de leitura e decodificação")

    try:
        etapa("2", "Abrir e ler o arquivo original")
        with open(path, "r", encoding="utf-8") as f:
            linhas = f.readlines()
        print(f"✅ Arquivo '{path}' aberto com sucesso! Total de linhas: {len(linhas)}\n")

        etapa("3", "Converter o conteúdo em blocos de 8 bits (zfill)")
        todas_linhas_8bits = [[p.zfill(8) for p in re.split(r'\s+', l.strip()) if p] for l in linhas]
        print("✅ Linhas convertidas em sequências de 8 bits!\n")

        etapa("4", "Decodificar o conteúdo em texto e salvar como 'encoded_message.txt'")
        texto_decodificado_linhas = ["".join(ascii_dict.get(p, '?') for p in linha_bits) for linha_bits in todas_linhas_8bits]
        print("🧩 Texto decodificado:")
        for i, linha in enumerate(texto_decodificado_linhas, start=1):
            print(f"{i:03d}: {linha}")

        tokens = [t for linha in texto_decodificado_linhas for t in re.split(r'\s+', linha.strip()) if t]
        with open("encoded_message.txt", "w", encoding="utf-8") as f:
            for token in tokens:
                f.write(f"{token}\n")
        print("\n✅ Palavras salvas (uma por linha) em 'encoded_message.txt'\n")

        ranking_real = imprimir_ranking_letras(texto_decodificado_linhas)
        texto_transformado = substituir_por_frequencia_final(texto_decodificado_linhas, ranking_real)
        salvar_e_imprimir_words_per_line(texto_transformado, "message.txt")

        etapa("10", "Encerrar o processo e exibir mensagem final")
        print("\n🏁 Processo completo finalizado com sucesso!\n")

    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo '{path}' não foi encontrado.")
    except Exception as e:
        print(f"⚠️ Ocorreu um erro inesperado: {e}")

# ===============================
# EXECUÇÃO
# ===============================
if __name__ == "__main__":
    processar_encoded_file("encoded.txt")
