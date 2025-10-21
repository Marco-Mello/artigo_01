# ================================================================
# funcoes_decodificador.py — funções utilitárias usadas por decrypt.py
#
# Contém funções para:
#  - padronizar sequências para 8 bits
#  - decodificar via dicionário binário->caractere
#  - associar palavras a posições (Passo 4) com tratamento de '--', '-', "'"
#  - ordenar palavras em blocos intercalados (Passo 5)
#  - gerar e aplicar mapeamentos (Passos 6..10)
#  - cálculo de impacto e busca de candidatas compatíveis
#  - restauração por posição (Passo 11/13)
#  - aplicar mapeamento a texto completo (Passo 14 helper)
# ================================================================

from collections import defaultdict
import unicodedata
import re

# ---------------------------
# Passo 2: padronização 8 bits
# ---------------------------
def padronizar_para_8bits(sequencias):
    """
    Recebe lista de sequências (strings) e retorna lista onde cada sequência
    foi 'padronizada' para múltiplos de 8 bits, adicionando zeros à esquerda.
    Também remove espaços antes da padronização (comportamento do pipeline).
    """
    sequencias_padronizadas = []
    for seq in sequencias:
        seq = seq.strip()
        seq = seq.replace(" ", "")
        while len(seq) % 8 != 0:
            seq = "0" + seq
        sequencias_padronizadas.append(seq)
    return sequencias_padronizadas


# ---------------------------
# Passo 3: buscar e substituir por dicionário bin->char
# ---------------------------
def buscar_e_substituir_por_dicionario(sequencias_padronizadas, caracteres_printaveis, unknown_char="?"):
    """
    Converte cada sequência binária (múltiplos de 8 bits) em texto usando
    o dicionário `caracteres_printaveis` (chave: '01000001' -> valor: 'A').
    Retorna lista de strings decodificadas.
    """
    resultados = []

    if not isinstance(caracteres_printaveis, dict):
        raise TypeError("caracteres_printaveis deve ser um dict binario->caractere")

    for seq in sequencias_padronizadas:
        texto = []
        for i in range(0, len(seq), 8):
            byte = seq[i:i+8]
            if len(byte) != 8:
                byte = byte.rjust(8, "0")
            caractere = caracteres_printaveis.get(byte, unknown_char)
            texto.append(caractere)
        resultados.append("".join(texto))

    return resultados


# ---------------------------
# Helpers de limpeza / normalização para Passo 4
# ---------------------------
def _remover_acentos(s: str) -> str:
    """
    Normaliza string Unicode e remove marcas diacríticas (acentos).
    Retorna string sem acentos.
    """
    nkfd = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in nkfd if not unicodedata.combining(ch))


def _limpar_token_por_regras(token: str) -> (str, str):
    """
    Aplica as regras solicitadas para limpar um token e retorna (token_limpo, suffix).
    Regras aplicadas:
      1) Procura (na prioridade): duplo traço '--', apóstrofo ("'", "’", "`"), ou traço '-'.
         - Se o símbolo for seguido de letra, corta no símbolo e devolve o sufixo removido
           (incluindo o símbolo) como `suffix`. Ex: "HAHS'S" -> ("HAHS", "'S"),
           "WORD-ING" -> ("WORD", "-ING"), "X--Y" -> ("X", "--Y").
         - Se o símbolo existir mas NÃO for seguido de letra, remove apenas o símbolo.
      2) Remove acentos (normalização).
      3) Mantém apenas letras A-Z (remove vírgulas, pontos, números, parênteses, etc).
      4) Retorna token_limpo (pode ser string vazia) e suffix (string com o símbolo+resto ou "").
    Observação: preserva capitalização original (não converte para lower/upper).
    """
    if not token:
        return "", ""

    suffix = ""
    # procurar primeiro ocorrência dentre '--' ou um dos símbolos (' \' \u2019 ` -')
    # a regex prioriza '--' colocando-o primeiro
    m = re.search(r"(--|[\'\u2019`-])", token)
    if m:
        pos = m.start()
        sym = m.group(1)  # pode ser '--' ou um símbolo único
        sym_len = len(sym)
        # se símbolo for seguido de letra (aceitamos acentuadas), cortamos e guardamos o sufixo
        if pos + sym_len < len(token) and re.match(r"[A-Za-z\u00C0-\u017F]", token[pos + sym_len]):
            suffix = token[pos:]  # inclui o(s) símbolo(s) e o resto
            token = token[:pos]
        else:
            # se não há letra depois, removemos apenas o(s) símbolo(s)
            token = token[:pos] + token[pos+sym_len:]

    # remover acentos
    token_sem_acentos = _remover_acentos(token)

    # manter apenas letras
    token_limpo = re.sub(r'[^A-Za-z]', '', token_sem_acentos)

    return token_limpo, suffix


# ---------------------------
# Passo 4 - associar palavras com posição (devolve original_lines_by_pos)
# ---------------------------
def associar_palavras_com_posicao(sequencias):
    """
    Passo 4 - Associar cada linha a uma palavra e lembrar a posição.

    Comportamento:
      - Une as sequências decodificadas (remove \r).
      - Substitui espaços por quebras de linha para criar tokens (mantendo lógica anterior).
      - Para cada linha/token:
          * guarda a linha original em original_lines_by_pos[idx] (antes da limpeza)
          * aplica regras de limpeza com apóstrofo/traço/-- (sufixo)
          * se resultado não-vazio, adiciona (idx, token_limpo) em palavras_pos
      - idx é incrementado para cada token (mesmo quando limpeza gera vazio — preserva posições)
    Retorna:
      - palavras_pos: lista de (posicao_original, palavra_limpa)
      - original_lines_by_pos: dict posicao -> linha_original (string)
    """
    texto_unido = "".join(seq.replace("\r", "") for seq in sequencias)
    texto_formatado = texto_unido.replace(" ", "\n")

    palavras_pos = []
    original_lines_by_pos = {}
    idx = 0

    for linha in texto_formatado.splitlines():
        linha_original = linha
        linha = linha.strip()
        original_lines_by_pos[idx] = linha_original

        if not linha:
            idx += 1
            continue

        token_limpo, suffix = _limpar_token_por_regras(linha)

        if token_limpo:
            palavras_pos.append((idx, token_limpo))
        idx += 1

    return palavras_pos, original_lines_by_pos


# ---------------------------
# Passo 5 - ordenando palavras por tamanho em blocos (intercalado)
# ---------------------------
def ordenar_palavras_por_tamanho_em_blocos(palavras_pos):
    """
    Agrupa palavras por comprimento mantendo (pos, palavra) e produz:
      - blocos: lista de rodadas; cada rodada é uma lista de (pos, palavra),
        contendo no máximo 1 palavra de cada tamanho (menor -> maior).
      - flat: lista única com todas as tuplas na ordem intercalada.
    """
    grupos = defaultdict(list)
    for pos, p in sorted(palavras_pos, key=lambda x: len(x[1])):
        grupos[len(p)].append((pos, p))

    tamanhos = sorted(grupos.keys())
    blocos = []

    while any(grupos[t] for t in tamanhos):
        rodada = []
        for t in tamanhos:
            if grupos[t]:
                rodada.append(grupos[t].pop(0))
        if rodada:
            blocos.append(rodada)

    flat = [item for bloco in blocos for item in bloco]
    return blocos, flat


# ---------------------------
# Aplicação de substituições por bloco (utilitária)
# ---------------------------
def aplicar_substitucoes_por_bloco(blocos, flat, top_words, bloco_index=0, apply_scope='block', used_top_words=None):
    """
    Gera mapeamentos usando APENAS as palavras do bloco `bloco_index`
    e aplica as substituições conforme `apply_scope`.
    Retorna (palavras_substituidas_pos, mapa)
    """
    if not isinstance(top_words, dict):
        raise TypeError("top_words deve ser um dict palavra->rank")

    if used_top_words is None:
        used_top_words = set()

    if bloco_index < 0 or bloco_index >= len(blocos):
        return flat.copy(), {}

    top_sorted = sorted(top_words.items(), key=lambda item: item[1])

    mapa = {}
    letras_usadas = set()

    def primeira_candidata_por_tamanho_disponivel(tamanho):
        for w, _rank in top_sorted:
            if len(w) == tamanho and w not in used_top_words:
                return w
        return None

    bloco = blocos[bloco_index]
    for pos, palavra in bloco:
        if palavra.islower():
            continue

        candidata = primeira_candidata_por_tamanho_disponivel(len(palavra))
        if not candidata:
            continue

        for c_cifrado, c_claro in zip(palavra, candidata):
            c_claro_lower = c_claro.lower()
            if c_cifrado.islower():
                continue
            if c_cifrado in mapa and mapa[c_cifrado] != c_claro_lower:
                continue
            if c_claro_lower in letras_usadas:
                continue
            mapa[c_cifrado] = c_claro_lower
            letras_usadas.add(c_claro_lower)
        used_top_words.add(candidata)

    pos_to_word = {pos: pw for pos, pw in flat}
    if apply_scope == 'block':
        pos_targets = {pos for pos, _ in bloco}
    else:
        pos_targets = set(pos_to_word.keys())

    for pos in pos_targets:
        palavra = pos_to_word.get(pos, "")
        if not palavra:
            continue
        nova = "".join(mapa.get(ch, ch) for ch in palavra)
        pos_to_word[pos] = nova

    palavras_substituidas_pos = [(pos, pos_to_word.get(pos, "")) for pos, _ in flat]
    return palavras_substituidas_pos, mapa


# ---------------------------
# Funções step-by-step para aplicar 1 mapeamento de cada vez
# ---------------------------
def gerar_mapeamentos_por_bloco(bloco, top_words, used_top_words=None):
    if not isinstance(top_words, dict):
        raise TypeError("top_words deve ser um dict palavra->rank")
    if used_top_words is None:
        used_top_words = set()

    top_sorted = sorted(top_words.items(), key=lambda item: item[1])
    mapa = {}
    letras_usadas = set()
    mapeamentos = []

    def primeira_candidata_disponivel(tamanho):
        for w, _rank in top_sorted:
            if len(w) == tamanho and w not in used_top_words:
                return w
        return None

    for pos, palavra in bloco:
        if palavra.islower():
            continue
        candidata = primeira_candidata_disponivel(len(palavra))
        if not candidata:
            continue
        for c_cifrado, c_claro in zip(palavra, candidata):
            c_claro_lower = c_claro.lower()
            if c_cifrado.islower():
                continue
            if c_cifrado in mapa:
                if mapa[c_cifrado] == c_claro_lower:
                    continue
                else:
                    continue
            if c_claro_lower in letras_usadas:
                continue
            mapa[c_cifrado] = c_claro_lower
            letras_usadas.add(c_claro_lower)
            mapeamentos.append((c_cifrado, c_claro_lower))
        used_top_words.add(candidata)

    return mapeamentos


def gerar_mapeamentos_para_primeira_palavra(bloco, top_words, used_top_words=None):
    if not isinstance(top_words, dict):
        raise TypeError("top_words deve ser um dict palavra->rank")
    if used_top_words is None:
        used_top_words = set()

    primeira = None
    for pos, palavra in bloco:
        if not palavra.islower():
            primeira = palavra
            break

    if primeira is None:
        return [], None

    top_sorted = sorted(top_words.items(), key=lambda item: item[1])

    tamanho = len(primeira)
    candidata = None
    for w, _rank in top_sorted:
        if len(w) == tamanho and w not in used_top_words:
            candidata = w
            break

    if candidata is None:
        return [], None

    mapeamentos = []
    for c_cifrado, c_claro in zip(primeira, candidata):
        c_claro_lower = c_claro.lower()
        if c_cifrado.islower():
            continue
        if c_cifrado == c_claro_lower:
            continue
        mapeamentos.append((c_cifrado, c_claro_lower))

    return mapeamentos, candidata


def aplicar_um_mapeamento_em_posicoes(flat, mapeamento, pos_targets):
    c_cifrado, c_claro = mapeamento
    partial_map = {c_cifrado: c_claro}
    pos_to_word = {pos: pw for pos, pw in flat}
    for pos in pos_targets:
        palavra = pos_to_word.get(pos, "")
        if not palavra:
            continue
        nova = "".join(partial_map.get(ch, ch) for ch in palavra)
        pos_to_word[pos] = nova
    novo_flat = [(pos, pos_to_word.get(pos, "")) for pos, _ in flat]
    return novo_flat


def aplicar_mapeamentos_em_posicoes(flat, mapeamentos, pos_targets):
    if not mapeamentos:
        return flat.copy()
    parcial = {c: v for c, v in mapeamentos}
    pos_to_word = {pos: pw for pos, pw in flat}
    for pos in pos_targets:
        palavra = pos_to_word.get(pos, "")
        if not palavra:
            continue
        nova = "".join(parcial.get(ch, ch) for ch in palavra)
        pos_to_word[pos] = nova
    novo_flat = [(pos, pos_to_word.get(pos, "")) for pos, _ in flat]
    return novo_flat


# ---------------------------
# Impacto / seleção de próxima candidata
# ---------------------------
def calcular_impacto_por_bloco(bloco, flat_before, flat_after, exclude_positions=None):
    if exclude_positions is None:
        exclude_positions = set()
    else:
        exclude_positions = set(exclude_positions)

    before_map = {pos: pw for pos, pw in flat_before}
    after_map = {pos: pw for pos, pw in flat_after}

    resultados = []
    for pos, _ in bloco:
        if pos in exclude_positions:
            continue

        b = before_map.get(pos, "")
        a = after_map.get(pos, "")

        # ignora se after já está totalmente minúscula (já 'resolvida')
        if a and a.islower():
            continue

        if not b:
            continue

        diffs = sum(1 for i, ch in enumerate(b) if i < len(a) and a[i] != ch)
        if len(a) < len(b):
            diffs += sum(1 for i in range(len(a), len(b)))
        frac = diffs / len(b) if len(b) > 0 else 0.0
        resultados.append({
            "pos": pos,
            "before": b,
            "after": a,
            "diff_count": diffs,
            "diff_frac": frac
        })

    resultados.sort(key=lambda x: (-x["diff_frac"], -x["diff_count"], x["pos"]))
    return resultados


def encontrar_candidata_compatível(palavra_atual, top_sorted, mapa_existente, letras_usadas, used_top_words=None):
    if palavra_atual.islower():
        return None, []

    tamanho = len(palavra_atual)
    if used_top_words is None:
        used_top_words = set()

    for w, _rank in top_sorted:
        if len(w) != tamanho:
            continue
        if w in used_top_words:
            continue

        possivel = True
        novos = []

        for i, (c_atual, c_cand) in enumerate(zip(palavra_atual, w)):
            c_claro_lower = c_cand.lower()

            if c_atual.islower():
                if c_atual != c_claro_lower:
                    possivel = False
                    break
                else:
                    continue

            if c_atual in mapa_existente:
                if mapa_existente[c_atual] != c_claro_lower:
                    possivel = False
                    break
                else:
                    continue

            if c_claro_lower in letras_usadas:
                possivel = False
                break

            if c_atual.islower():
                possivel = False
                break

            novos.append((c_atual, c_claro_lower))

        if possivel:
            return w, novos

    return None, []


# ---------------------------
# Passo 14 helper: aplicar mapeamento a um texto completo
# ---------------------------
def aplicar_mapeamento_em_texto(texto: str, mapa_substituicao: dict) -> str:
    """
    Aplica o mapa_substituicao a um texto completo, substituindo apenas
    caracteres MAIÚSCULOS que existam como chaves no mapa_substituicao.
    Chaves esperadas: caracteres simples (ex: 'T') -> valores: 'a' (lowercase).
    - percorre cada caractere do texto; se MAIÚSCULO e existe mapping (key)
      substitui pelo valor.
    - retorna o texto resultante.
    """
    if not mapa_substituicao:
        return texto

    # normalizar mapa: apenas pares (1-char -> 1-char) válidos
    mapa_clean = {k: v for k, v in mapa_substituicao.items() if isinstance(k, str) and isinstance(v, str) and len(k) == 1 and len(v) == 1}

    if not mapa_clean:
        return texto

    out = []
    for ch in texto:
        if ch.isupper():
            # checar chave exatamente igual (maiusc), depois upper/lower por segurança
            if ch in mapa_clean:
                out.append(mapa_clean[ch])
            elif ch.upper() in mapa_clean:
                out.append(mapa_clean[ch.upper()])
            elif ch.lower() in mapa_clean:
                out.append(mapa_clean[ch.lower()])
            else:
                out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------
# Passo 11 helper: restauração por posição
# ---------------------------
def restaurar_por_posicao(palavras_pos):
    if not palavras_pos:
        return []
    max_pos = max(pos for pos, _ in palavras_pos)
    resultado = [""] * (max_pos + 1)
    for pos, palavra in palavras_pos:
        resultado[pos] = palavra
    return resultado
