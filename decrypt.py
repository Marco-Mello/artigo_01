import funcoes_decodificador as fd


fd.limpar_pastas_de_trabalho()

# -----------------------------
# PASSO 0 — Configurações
# -----------------------------
# Arquivos / parâmetros principais (edite se necessário)
BINARIO_SRC = "encoded_01.txt"
FONTE = "mensagens/5_4_3_2_1_0_encoded_em_linhas.py"
TOP_WORDS = "top_words_banco_de_palavras.py"
THRESHOLDS = (75.0, 66.0, 50.0, 33.0, 25.0, 10.0)

# -----------------------------
# PASSO 1 — Importar / copiar binário para mensagens/
# -----------------------------
# Lê o arquivo binário/texto original e gera mensagens/0_encoded.txt
binario = fd.ler_arquivo_binario(BINARIO_SRC)

# -----------------------------
# PASSO 2 — Decodificar binário → ASCII e preparar tokens
# -----------------------------
# Gera:
#  - mensagens/1_0_encoded_em_linhas  (bytes por linha)
#  - mensagens/2_1_0_encoded_em_linhas (ASCII com espaços→linhas)
analisar = fd.decodificar_binario_para_ascii("mensagens/0_encoded.txt")

# Normaliza tokens deixando cada token em sua própria linha:
# gera mensagens/3_2_1_0_encoded_em_linhas.txt
tratar = fd.tratamento_palavras("mensagens/2_1_0_encoded_em_linhas.txt")

# Cria matriz ["palavra", pos] a partir do arquivo em linhas:
# gera mensagens/4_3_2_1_0_encoded_em_linhas.py
listas = fd.criar_listas_palavras_posicoes("mensagens/3_2_1_0_encoded_em_linhas.txt")

# Ordena a matriz e salva com prefixo 5_ (preservando escapes)
# gera mensagens/5_4_3_2_1_0_encoded_em_linhas.py
ordenar = fd.ordenar_matriz("mensagens/4_3_2_1_0_encoded_em_linhas.py")

# -----------------------------
# PASSO 3 — Pipeline principal (1 letra + 2 letras / subloops)
# -----------------------------
# Executa o fluxo padrão que tenta mapear 1 letra (A/I), depois 2-letras (subloops)
# Retorna True se algum subloop produziu mapeamentos aplicáveis; False caso contrário.
sucesso = fd.executar_pipeline_decifrado(
    fonte=FONTE,
    top_words_path=TOP_WORDS,
    thresholds_to_run=THRESHOLDS
)

# -----------------------------
# PASSO 4 — Fallback 3-letras (quando pipeline principal falha)
# -----------------------------
# Se o pipeline padrão não obtiver mapeamentos, executa o fallback 3-letras
# (essa função encapsula todo o processo: aplicar cada palavra, salvar maps/dec,
#  executar thresholds por passo e imprimir resumo).
if not sucesso:
    resultado_fallback = fd.executar_fallback_3_letras(
        fonte=FONTE,
        top_words_path=TOP_WORDS,
        thresholds_to_run=THRESHOLDS,
        mapping_base={},                     # estado inicial para cada candidate
        accumulate_between_candidates=False  # False -> cada candidate é testado isoladamente
    )

# -----------------------------
# PASSO 5 — Análise dos arquivos gerados (decifrados/)
# -----------------------------
# Função que varre os arquivos em decifrados/ e imprime um resumo por arquivo.
fd.analisar_decifrados_completo()

# -----------------------------
# PASSO 6 — Selecionar e gerar texto final limpo
# -----------------------------
# Escolhe o melhor .py decifrado (maior pct traduzido), ordena por posição e gera:
#   encoded_decifrado.txt (palavras em sequência separadas por espaço)
fd.imprimir_melhor_texto()

# -----------------------------
# FIM — Mensagem de encerramento
# -----------------------------
print("\nProcessamento concluído. Verifique a pasta 'decifrados/', 'mapeamentos/' e 'palavrasUsadas/'.")
