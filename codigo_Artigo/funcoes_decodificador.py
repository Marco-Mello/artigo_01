# ================================================================
# funcoes_decodificador.py — funções utilitárias usadas por decrypt.py
# Alteração: associar_palavras_com_posicao agora normaliza e filtra
#            mantendo apenas letras; trata apóstrofos como pedido.
# ================================================================

from collections import defaultdict
import unicodedata
import re

def padronizar_para_8bits(sequencias):
    """
    Recebe lista de sequências (strings) e retorna lista onde cada sequência
    foi 'padronizada' para múltiplos de 8 bits, adicionando zeros à esquerda.
    Também remove espaços antes da padronização.
    """
    sequencias_padronizadas = []
    for seq in sequencias:
        seq = seq.strip()
        seq = seq.replace(" ", "")
        while len(seq) % 8 != 0:
            seq = "0" + seq
        sequencias_padronizadas.append(seq)
    return sequencias_padronizadas


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


def _remover_acentos(s: str) -> str:
    """
    Normaliza string Unicode e remove marcas diacríticas (acentos).
    Retorna string sem acentos.
    """
    nkfd = unicodedata.normalize('NFD', s)
    return ''.join(ch for ch in nkfd if not unicodedata.combining(ch))


def _limpar_token_por_regras(token: str) -> str:
    """
    Aplica as regras solicitadas para limpar um token:
      1) Se existir apóstrofo "'" seguido de letra, corta no primeiro apóstrofo.
         Ex: "HAHS'S" -> "HAHS"
      2) Remove acentos (normalização).
      3) Mantém apenas letras A-Z (removendo vírgulas, pontos, números, parênteses, etc).
      4) Retorna string resultante (pode ser vazia).
    Observação: preserva capitalização original (não força lower/upper).
    """
    if not token:
        return ""

    # 1) cortar no primeiro apóstrofo se houver
    if "'" in token:
        token = token.split("'", 1)[0]

    # 2) remover acentos
    token = _remover_acentos(token)

    # 3) manter apenas letras (A-Z, a-z) — remove todo o resto
    token = re.sub(r'[^A-Za-z]', '', token)

    return token


def associar_palavras_com_posicao(sequencias):
    """
    Passo 4 - Associar cada linha a uma palavra e lembrar a posição.

    Comportamento atualizado:
      - Une todas as sequências decodificadas (remove \n e \r antes de processar).
      - Substitui espaços por quebras de linha (como antes).
      - Para cada linha/token:
          * Se existir apóstrofo (') corta no apóstrofo (ex: HAHS'S -> HAHS)
          * Remove acentos
          * Remove qualquer caractere que não seja letra (pontuação, números, etc.)
      - Retorna lista de tuplas (posicao_original, palavra_limpa) com posições 0-based.
    """
    texto_unido = "".join(seq.replace("\r", "") for seq in sequencias)
    # substitui espaços por quebras de linha (mantendo lógica anterior)
    texto_formatado = texto_unido.replace(" ", "\n")

    palavras_pos = []
    idx = 0
    for linha in texto_formatado.splitlines():
        linha = linha.strip()
        if not linha:
            idx += 1
            continue

        # aplicar limpeza por token (trata apóstrofo e filtra apenas letras)
        token_limpo = _limpar_token_por_regras(linha)

        if token_limpo:
            palavras_pos.append((idx, token_limpo))
        # mesmo que o token limpo seja vazio, contamos a posição (idx incrementa)
        idx += 1

    return palavras_pos


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


def aplicar_substitucoes_por_bloco(blocos, flat, top_words, bloco_index=0, apply_scope='block', used_top_words=None):
    """
    Gera mapeamentos usando APENAS as palavras do bloco `bloco_index`
    e aplica as substituições conforme `apply_scope`:
      - 'block' -> aplica somente no bloco
      - 'all' -> aplica em todo o flat

    used_top_words: set opcional de palavras do top_words já usadas (para não reutilizar)
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
        # regra: não processar palavras já totalmente minúsculas
        if palavra.islower():
            continue

        candidata = primeira_candidata_por_tamanho_disponivel(len(palavra))
        if not candidata:
            continue

        for c_cifrado, c_claro in zip(palavra, candidata):
            c_claro_lower = c_claro.lower()
            if c_cifrado.islower():
                # não criamos mapeamentos para caracteres já minúsculos
                continue
            if c_cifrado in mapa and mapa[c_cifrado] != c_claro_lower:
                continue
            if c_claro_lower in letras_usadas:
                continue
            mapa[c_cifrado] = c_claro_lower
            letras_usadas.add(c_claro_lower)
        # marca candidata como usada
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
    """
    Gera lista ordenada de mapeamentos (cifrado -> claro) a partir das palavras do bloco.
    Regras:
      - pula palavras totalmente minúsculas (não substitui).
      - não cria mapeamento para caracteres cifrados que já estão minúsculos.
      - não reutiliza top_words já em used_top_words.
      - evita sobrescrever cifrados ou reutilizar destino já usado.
    Retorna lista de (c_cifrado, c_claro).
    """
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
    """
    Gera mapeamentos apenas para a PRIMEIRA palavra do bloco que não esteja
    totalmente em minúsculas. Retorna (mapeamentos, candidata_word).
    Respeita used_top_words (não reutilizar palavras do dicionário).
    NÃO cria mapeamento para caracteres cifrados já em minúsculo.
    """
    if not isinstance(top_words, dict):
        raise TypeError("top_words deve ser um dict palavra->rank")

    if used_top_words is None:
        used_top_words = set()

    # encontra a primeira palavra do bloco que não esteja toda em minúsculas
    primeira = None
    primeira_pos = None
    for pos, palavra in bloco:
        if not palavra.islower():
            primeira = palavra
            primeira_pos = pos
            break

    if primeira is None:
        return [], None  # nenhuma palavra válida no bloco

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
        # evita mapeamento identidade e evita mapear cifrados já minúsculos
        if c_cifrado.islower():
            continue
        if c_cifrado == c_claro_lower:
            continue
        mapeamentos.append((c_cifrado, c_claro_lower))

    # retornamos também a candidata para que o chamador possa marcar used_top_words
    return mapeamentos, candidata


def aplicar_um_mapeamento_em_posicoes(flat, mapeamento, pos_targets):
    """
    Aplica UM mapeamento (cifrado -> claro) nas posições indicadas.
    Retorna novo flat.
    """
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
    """
    Aplica múltiplos mapeamentos (lista de (cifrado, claro)) nas posições alvo.
    Retorna novo flat.
    """
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
    """
    Calcula impacto por palavra no bloco:
      - bloco: lista de (pos, palavra_original_do_bloco)
      - flat_before: lista linear [(pos, palavra)] antes da substituição
      - flat_after:  lista linear [(pos, palavra)] depois da substituição
      - exclude_positions: conjunto de posições a serem ignoradas (opcional)

    Regras:
      - ignora posições em exclude_positions
      - ignora entradas cujo 'after' já esteja completamente em minúsculas
    Retorna lista de dicts ordenada por diff_frac desc, diff_count desc, pos asc.
    """
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
    """
    Dado uma palavra atual (contendo já substituições parciais), busca a primeira
    candidata em top_sorted (lista de (word, rank)) com mesmo comprimento que seja
    compatível com o mapa_existente e letras_usadas, e que NÃO esteja em used_top_words.

    Regras:
      - se palavra_atual estiver totalmente minúscula -> retorna (None, []).
      - se em alguma posição palavra_atual[i] for minúscula, a candidata deve ter
        exatamente o mesmo caractere (em lower) naquela posição.
      - para posições cujo caractere atual é maiúsculo (cifrado), permite-se criar
        novos mapeamentos: desde que o destino não esteja em letras_usadas e não
        conflite com mapa_existente.
      - não tenta criar mapeamentos para caracteres cifrados que já sejam minúsculos.
    Retorna (candidata_word, mapeamentos_novos_list) ou (None, []) se não achar.
    """
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

            # se a posição já está revelada (minúscula) -> deve coincidir
            if c_atual.islower():
                if c_atual != c_claro_lower:
                    possivel = False
                    break
                else:
                    continue

            # se o caractere atual possui mapeamento existente -> deve ser consistente
            if c_atual in mapa_existente:
                if mapa_existente[c_atual] != c_claro_lower:
                    possivel = False
                    break
                else:
                    continue

            # se chegamos aqui, posição livre: não permitir destino já usado
            if c_claro_lower in letras_usadas:
                possivel = False
                break

            # não criar mapeamento para cifrados que já são minúsculos (defesa)
            if c_atual.islower():
                possivel = False
                break

            novos.append((c_atual, c_claro_lower))

        if possivel:
            return w, novos

    return None, []


def restaurar_por_posicao(palavras_pos):
    """
    Recebe lista de (posicao, palavra) e retorna lista com as palavras
    posicionadas na ordem original (index -> palavra).
    """
    if not palavras_pos:
        return []
    max_pos = max(pos for pos, _ in palavras_pos)
    resultado = [""] * (max_pos + 1)
    for pos, palavra in palavras_pos:
        resultado[pos] = palavra
    return resultado
