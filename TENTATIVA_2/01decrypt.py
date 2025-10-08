import re
import time
import sys
from collections import Counter

# importa o dicionário de ranking (não usado nesta versão)
try:
    from top_words import english_rank
except Exception:
    english_rank = {}

# ===============================
# Função auxiliar: barra de progresso
# ===============================
def barra_progresso(duracao=1, largura=20):
    etapas = 20
    intervalo = duracao / etapas
    for i in range(etapas + 1):
        porcentagem = int((i / etapas) * 100)
        barra = "█" * i + "-" * (largura - i)
        sys.stdout.write(f"\r   [{barra}] {porcentagem}%")
        sys.stdout.flush()
        time.sleep(intervalo)
    print()  # quebra de linha ao final

# ===============================
# DICIONÁRIO ASCII
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

# ===============================
# Função principal
# ===============================
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

        # Etapa final sem barra
        print("6 - Processo finalizado com sucesso!")

    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo '{path}' não foi encontrado.")
    except Exception as e:
        print(f"⚠️ Ocorreu um erro: {e}")

# ===============================
# EXECUÇÃO
# ===============================
if __name__ == "__main__":
    processar_encoded_file("encoded.txt")
