"""
decrypt.py
Função que analisa um texto decifrado e:
- Conta quantas palavras correspondem ao banco de palavras conhecido (top_words_banco_de_palavras)
- Conta o total de palavras válidas
- Mede a quantidade de letras minúsculas (indicando o quanto do texto já foi decifrado)
"""

DEBUG = False  # Se True, exibe mensagens detalhadas; se False, executa silenciosamente


import re  # Módulo para expressões regulares (usado para limpeza e separação de texto)
import os
from top_words_banco_de_palavras import top_words_banco_de_palavras  # Importa o dicionário de palavras conhecidas





from pathlib import Path
from importlib.machinery import SourceFileLoader

from importlib.util import spec_from_loader, module_from_spec
import importlib.util
from collections import Counter, defaultdict
from typing import Dict, Tuple, List, Optional


























def _load_top_words(path: str) -> Dict[str,int]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de top words não encontrado: {path}")
    spec = importlib.util.spec_from_file_location("top_words_mod", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tbl = getattr(mod, "top_words_banco_de_palavras", None)
    if not isinstance(tbl, dict):
        raise ValueError("O arquivo top_words_banco_de_palavras.py não contém um dicionário válido chamado 'top_words_banco_de_palavras'.")
    return {k.upper(): int(v) for k, v in tbl.items()}

def _best_candidate_for_token_strict_local(token_display: str, top_words: Dict[str,int]) -> Optional[str]:
    L = len(token_display)
    known = {i: ch.upper() for i, ch in enumerate(token_display) if ch.islower()}
    candidates = [w for w in top_words.keys() if len(w) == L]
    if not candidates:
        return None
    compat = []
    for cand in candidates:
        ok = True
        for i, val in known.items():
            if cand[i] != val:
                ok = False
                break
        if ok:
            compat.append(cand)
    if not compat:
        return None
    compat.sort(key=lambda w: -top_words.get(w, 0))
    return compat[0]

def subloop_action_find_best_word(mapping_ext: Dict[str,str],
                                  map_path: Path,
                                  dec_path: Path,
                                  fonte: str,
                                  token: str,
                                  prefix_base: str,
                                  top_words_path: str = "mensagens/top_words_banco_de_palavras.py"
                                  ) -> List[Tuple[str,int,int,int,float,Optional[str]]]:
    """
    Versão que garante:
      - mesma token_display recebe a mesma palavra atribuída em todas as ocorrências;
      - não atribui palavra quando pct == 0.0 (a menos que token_display já possua atribuição);
      - não reutiliza uma palavra do dicionário para tokens diferentes dentro do mesmo subloop.
    Retorna lista de tuples (token_display, length, mapped_count, total, pct, best_or_None)
    e imprime linhas compactas.
    """
    # carrega dicionário
    p = Path(top_words_path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo de top words não encontrado: {top_words_path}")

    spec = importlib.util.spec_from_file_location("top_words_mod", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    top_words = getattr(mod, "top_words_banco_de_palavras", None)
    if not isinstance(top_words, dict):
        raise ValueError("O arquivo top_words_banco_de_palavras.py não contém um dicionário válido chamado 'top_words_banco_de_palavras'.")
    top_words = {k.upper(): int(v) for k, v in top_words.items()}

    # obter resultados sem prints extras (todas as ocorrências)
    results = analyze_by_decreasing_lengths(fonte, mapping_ext, min_len=1, print_report=False)
    if not results:
        return []

    used_words = set()            # palavras já atribuídas a outros token_display neste subloop
    assigned_by_token = dict()    # token_display -> palavra atribuída (reaplicable)

    def best_candidate_strict_no_reuse(token_display: str, pct: float) -> Optional[str]:
        """
        Retorna a palavra compatível de maior score que ainda não foi usada.
        Se pct == 0.0 retorna None.
        """
        if pct == 0.0:
            return None

        L = len(token_display)
        known = {i: ch.upper() for i, ch in enumerate(token_display) if ch.islower()}
        candidates = [w for w in top_words.keys() if len(w) == L]
        if not candidates:
            return None

        compat = []
        for cand in candidates:
            if cand in used_words:
                continue
            ok = True
            for i, val in known.items():
                if cand[i] != val:
                    ok = False
                    break
            if ok:
                compat.append(cand)

        if not compat:
            return None

        compat.sort(key=lambda w: -top_words.get(w, 0))
        return compat[0]

    output = []
    # itera nas ocorrências já ordenadas (cada ocorrência independente)
    for length, token_orig, mapped_count, total, pct, token_display in results:
        # se esta token_display já possui atribuição, reaplica-a
        if token_display in assigned_by_token:
            best = assigned_by_token[token_display]
            # caso a palavra atribuída tenha sido marcada como usada, ok — ela já pertence a este token_display
        else:
            # tenta achar candidata nova (não reutilizando palavras já atribuídas)
            best = best_candidate_strict_no_reuse(token_display, pct)
            if best is not None:
                # atribui e marca como usada (para impedir uso por outros token_display)
                assigned_by_token[token_display] = best
                used_words.add(best)
            else:
                best = None

        best_str = best if best is not None else "-"
        print(f"  - '{token_display}' (len={length}): {mapped_count}/{total} → {pct:.2f}% | {best_str} (melhor palavra)")
        output.append((token_display, length, mapped_count, total, pct, best if best is not None else None))

    return output











































def _extract_tokens_from_file(arquivo: str) -> List[str]:
    """
    Retorna lista de tokens (strings entre aspas) na ordem de ocorrência.
    """
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")
    text = src.read_text(encoding="utf-8")
    pattern = re.compile(r"""(['"])([A-Za-z0-9_]+)\1""")
    return [m.group(2) for m in pattern.finditer(text)]







def analyze_by_decreasing_lengths(arquivo: str, mapping_ext: Dict[str,str], min_len: int = 1,
                                  print_report: bool = True
                                 ) -> List[Tuple[int, str, int, int, float, str]]:
    """
    Versão que retorna UMA entrada por ocorrência no arquivo (não remove duplicatas).
    Cada tupla é:
      (length, token_original, mapped_count, total, pct, token_display)

    - arquivo: caminho do .py fonte
    - mapping_ext: dicionário {encoded_char: decoded_char}
    - min_len: menor comprimento a considerar
    - print_report: se True imprime resumo (caso contrário não imprime)
    """
    src = Path(arquivo)
    if not src.exists():
        if print_report:
            print(f"Arquivo não encontrado: {arquivo}")
        return []

    text = src.read_text(encoding="utf-8")

    # captura TODAS as ocorrências (mantém ordem)
    pattern = re.compile(r"""(['"])([A-Za-z0-9_]+)\1""")
    matches = list(pattern.finditer(text))
    if not matches:
        if print_report:
            print("Nenhum token/string encontrado no arquivo.")
        return []

    # monta lista de ocorrências como (token, start, end)
    occurrences = [(m.group(2), m.start(2), m.end(2)) for m in matches]

    # calcula resultado por ocorrência
    mapped_keys = set(mapping_ext.keys())
    results: List[Tuple[int, str, int, int, float, str]] = []

    for token, sstart, send in occurrences:
        total = len(token)
        if total < min_len:
            continue
        mapped_count = sum(1 for ch in token if ch in mapped_keys)
        pct = (mapped_count / total) * 100.0 if total > 0 else 0.0

        # token_display: substitui caracteres mapeados por letra decodificada em minúscula
        display_chars = []
        for ch in token:
            if ch in mapping_ext and isinstance(mapping_ext[ch], str) and mapping_ext[ch]:
                display_chars.append(mapping_ext[ch].lower())
            else:
                display_chars.append(ch)
        token_display = "".join(display_chars)

        results.append((len(token), token, mapped_count, total, pct, token_display))

    # ordena do maior % para o menor; em empate por comprimento decrescente e token
    results_sorted = sorted(results, key=lambda x: (-x[4], -x[0], x[1]))

    if print_report:
        print(f"\nAnálise geral (ordenada por maior porcentagem) em {arquivo}:")
        for _, token_orig, mapped_count, total, pct, token_display in results_sorted:
            print(f"  - '{token_display}' (len={total}): {mapped_count}/{total} → {pct:.2f}% |")

    return results_sorted




def analyze_longest_words(arquivo: str, mapping_ext: Dict[str,str]) -> List[Tuple[str,int,int,float]]:
    """
    - arquivo: caminho para o .py fonte (ex: mensagens/5_4_3_2_1_0_encoded_em_linhas.py)
    - mapping_ext: dicionário do tipo {encoded_char: decoded_char, ...}
    Retorna uma lista de tuplas para cada palavra de comprimento máximo:
      (token, letras_mapeadas, total_letras, porcentagem)
    Também imprime um resumo legível.
    """
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")

    text = src.read_text(encoding="utf-8")

    # regex que captura tokens entre aspas com letras/dígitos (ajuste se precisar)
    pattern = re.compile(r"""(['"])([A-Za-z0-9]+)\1""")
    tokens = [m.group(2) for m in pattern.finditer(text)]

    if not tokens:
        print("Nenhum token/string encontrado no arquivo.")
        return []

    # encontra o comprimento máximo
    max_len = max(len(t) for t in tokens)

    # filtra tokens com o comprimento máximo (mantemos ordem e removemos duplicatas mantendo primeira ocorrência)
    seen = set()
    longest_tokens = []
    for t in tokens:
        if len(t) == max_len and t not in seen:
            longest_tokens.append(t)
            seen.add(t)

    results = []
    mapped_keys = set(mapping_ext.keys())

    for token in longest_tokens:
        total = len(token)
        mapped_count = sum(1 for ch in token if ch in mapped_keys)
        pct = (mapped_count / total) * 100 if total > 0 else 0.0
        results.append((token, mapped_count, total, pct))

    # imprime resumo
    print(f"\nAnálise de tokens de comprimento máximo (={max_len}) em {arquivo}:")
    for token, mapped_count, total, pct in results:
        print(f"  - {token!r}: {mapped_count}/{total} letras mapeadas → {pct:.2f}%")

    return results





































































































































































def _load_matriz_from_py(path: str):
    spec = importlib.util.spec_from_file_location("mod_temp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "matriz", None)

def _write_map_file(map_dict: Dict[str,str], out_path: Path):
    out_path.parent.mkdir(exist_ok=True, parents=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Arquivo gerado automaticamente\n")
        f.write("final_map = {\n")
        for k, v in map_dict.items():
            f.write(f"    {k!r}: {v!r},\n")
        f.write("}\n")

def _apply_mapping_to_text(text: str, mapping_for_text: Dict[str,str]) -> str:
    # aplica substituições simples na ordem das keys; para evitar conflito de sobreposição
    # ordenamos por comprimento da key decrescente (maiores primeiro)
    for key in sorted(mapping_for_text.keys(), key=lambda s: -len(s)):
        text = text.replace(key, mapping_for_text[key])
    return text

def map_1_letra(arquivo: str, letra_destino: str = "A") -> Tuple[Dict[str,str], Path, Path]:
    # (mantém a implementação anterior, simplificada aqui para contexto)
    src = Path(arquivo)
    matriz = _load_matriz_from_py(arquivo)
    if matriz is None:
        raise ValueError("Arquivo não contém variável 'matriz'.")
    primeiro = None
    for item in matriz:
        if isinstance(item, (list, tuple)) and len(item) > 0:
            elem = item[0]
            if isinstance(elem, str) and len(elem) == 1:
                primeiro = elem
                break
    if not primeiro:
        return None, None, None

    mapping = {primeiro: letra_destino}
    prefix = f"{letra_destino}_"
    map_path = Path("mapeamentos") / f"{prefix}final_map.py"
    _write_map_file(mapping, map_path)

    text = src.read_text(encoding="utf-8")
    mapping_for_text = {k: v.lower() for k, v in mapping.items()}
    out_text = _apply_mapping_to_text(text, mapping_for_text)

    decifrado_path = Path("decifrados") / f"{prefix}decifrado.py"
    decifrado_path.parent.mkdir(exist_ok=True, parents=True)
    decifrado_path.write_text(out_text, encoding="utf-8")

    return mapping, map_path, decifrado_path

def map_2_letras(arquivo: str, mapping_base: Dict[str,str], duas_letras_token: str, prefix_base: str) -> Tuple[Dict[str,str], Path, Path]:
    """
    Comportamento:
    - Aplica temporariamente mapping_base ao texto do arquivo fonte.
    - Procura primeira ocorrência de uma string de 2 caracteres (entre aspas) cujo
      primeiro caractere == mapping_base[alguma_key].lower()  (ex: 'a')
    - Quando encontra, pega o segundo caractere dessa ocorrência NO ARQUIVO ORIGINAL
      (antes de aplicar o novo mapeamento) e cria mapping_ext adicionando:
          encoded_second_char -> segunda_letra_do_token
    - Salva mapeamentos/{prefix_base}{token}_final_map.py e decifrados/{prefix_base}{token}_decifrado.py
    - Retorna (mapping_ext, map_path, decifrado_path)
    """
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")

    # 1) determina a letra já mapeada (assumimos mapping_base tem exatamente 1 par do passo 1)
    if not mapping_base:
        raise ValueError("mapping_base vazio ou None")

    # pega a primeira (e principal) letra mapeada - por padrão é o primeiro item do dict
    base_src_char, base_dst = next(iter(mapping_base.items()))
    mapped_first_lower = base_dst.lower()

    # 2) lê original e cria versão com mapping_base aplicada
    original_text = src.read_text(encoding="utf-8")
    mapping_base_for_text = {k: v.lower() for k, v in mapping_base.items()}
    temp_text = _apply_mapping_to_text(original_text, mapping_base_for_text)

    # 3) procura a primeira ocorrência de string de 2 letras entre aspas cujo primeiro char == mapped_first_lower
    # Regex procura tokens entre aspas simples ou duplas: "XY" ou 'XY'
    pattern = re.compile(r"""(['"])([A-Za-z0-9]{2})\1""")
    encoded_second = None
    matched_token = None
    for m in pattern.finditer(temp_text):
        token = m.group(2)           # token visto no texto com mapping_base aplicado (p.ex: 'aX')
        if token[0] == mapped_first_lower:
            # encontramos; extrai a substring equivalente no original para identificar o encoded second char
            span_start, span_end = m.span(2)   # posição da token no temp_text
            # m.span gives positions relative to temp_text; assumimos mesmo comprimento/posições no original_text
            orig_token = original_text[span_start:span_end]  # pega token original (ex: "YZ" -> YZ)
            if len(orig_token) == 2:
                encoded_second = orig_token[1]   # caractere codificado que corresponde ao segundo da token
                matched_token = token
                break
            # se por algum motivo o original difere no comprimento, tentamos extrair via outro método:
            # alternativa: extrair o conteúdo entre as aspas diretamente no original com aproximação
    if encoded_second is None:
        print(f"Nenhuma palavra de 2 letras iniciando com '{mapped_first_lower}' foi encontrada.")
        return None, None, None

    # 4) monta mapeamento estendido
    segunda_letra_alvo = duas_letras_token[1]  # ex: 'S' em 'AS'
    mapping_ext = dict(mapping_base)            # ex: {'Y':'A'}
    mapping_ext[encoded_second] = segunda_letra_alvo  # ex: {'Y':'A', '<enc>':'S'}

    # 5) salva mapeamento estendido
    prefix = prefix_base  # ex: 'A_'
    map_path = Path("mapeamentos") / f"{prefix}{duas_letras_token}_final_map.py"
    _write_map_file(mapping_ext, map_path)

    # 6) aplica TODOS os mapeamentos ao original e salva (valores em minúsculas no texto)
    mapping_for_text = {k: v.lower() for k, v in mapping_ext.items()}
    out_text = _apply_mapping_to_text(original_text, mapping_for_text)
    decifrado_path = Path("decifrados") / f"{prefix}{duas_letras_token}_decifrado.py"
    decifrado_path.parent.mkdir(exist_ok=True, parents=True)
    decifrado_path.write_text(out_text, encoding="utf-8")

    print(f"Mapeamento estendido salvo em {map_path}: {mapping_ext}")
    print(f"Arquivo decifrado salvo em {decifrado_path} (token encontrado: {matched_token}, encoded_second='{encoded_second}')")

    return mapping_ext, map_path, decifrado_path



























































def _to_int_safe(v):
    """Tenta converter em int; se falhar, retorna +inf para que vá ao fim na ordem asc."""
    try:
        return int(v)
    except Exception:
        return float('inf')

def ordenar_matriz(matriz_ou_arquivo):
    """
    Ordena e salva automaticamente com prefixo '5_'.
    Regras:
      1) pontuação no final
      2) comprimento da palavra (asc)
      3) dentro de cada comprimento: tokens ordenados por número de ocorrências (desc)
      4) dentro de cada token: linhas ordenadas por item[1] (ASC)  <-- aqui é a mudança
    Garante que todas as linhas de um mesmo token fiquem juntas.
    """
    
    PONTUACOES = {'"', "'", '&', ',', '.', '-', '--', '`'}
    
    # --- carregar matriz ---
    if isinstance(matriz_ou_arquivo, (str, Path)):
        p = Path(matriz_ou_arquivo)
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {p}")

        loader = SourceFileLoader("tmp_encoded", str(p))
        spec = spec_from_loader(loader.name, loader)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)

        matriz = getattr(mod, "matriz", None)
        if matriz is None:
            raise AttributeError(f"Arquivo {p.name} não define a variável 'matriz'")
    else:
        matriz = matriz_ou_arquivo

    # --- preparar contagens e agrupamentos ---
    tokens = [str(item[0]) for item in matriz]
    occ_counter = Counter(tokens)

    items_normais = []
    items_pontuacao = []
    for item in matriz:
        palavra = "" if item[0] is None else str(item[0])
        if palavra in PONTUACOES:
            items_pontuacao.append(item)
        else:
            items_normais.append(item)

    grupos_por_len = defaultdict(lambda: defaultdict(list))
    for item in items_normais:
        palavra = "" if item[0] is None else str(item[0])
        l = len(palavra)
        grupos_por_len[l][palavra].append(item)

    # --- construir resultado respeitando as regras ---
    ordenada = []

    for comprimento in sorted(grupos_por_len.keys()):
        tokens_do_comprimento = grupos_por_len[comprimento]

        tokens_ordenados = sorted(
            tokens_do_comprimento.keys(),
            key=lambda t: (-occ_counter.get(t, 0), t)
        )

        for token in tokens_ordenados:
            itens_token = tokens_do_comprimento[token]
            # === mudança: ordenar por valor numérico ASC ===
            itens_token_ordenados = sorted(
                itens_token,
                key=lambda it: _to_int_safe(it[1])
            )
            ordenada.extend(itens_token_ordenados)

    # anexar pontuações ao final (mesma lógica: ordena tokens de pontuação por ocorrência e depois por valor ASC)
    if items_pontuacao:
        grupos_p_pont = defaultdict(list)
        for item in items_pontuacao:
            palavra = "" if item[0] is None else str(item[0])
            grupos_p_pont[palavra].append(item)

        tokens_p_ordenados = sorted(
            grupos_p_pont.keys(),
            key=lambda t: (-occ_counter.get(t, 0), t)
        )
        for token in tokens_p_ordenados:
            itens_token = grupos_p_pont[token]
            itens_token_ordenados = sorted(
                itens_token,
                key=lambda it: _to_int_safe(it[1])
            )
            ordenada.extend(itens_token_ordenados)

    # --- salvar automaticamente se a entrada foi um arquivo ---
    if isinstance(matriz_ou_arquivo, (str, Path)):
        nome_arquivo = Path(matriz_ou_arquivo)
        novo_nome = nome_arquivo.parent / f"5_{nome_arquivo.name}"
        with open(novo_nome, "w", encoding="utf-8") as f:
            f.write("matriz = [\n")
            for item in ordenada:
                palavra, numero = item
                f.write(f'    ["{palavra}", {numero}],\n')
            f.write("]\n")
       # print(f"✅ Matriz ordenada salva em: {novo_nome}")

    return ordenada



























def criar_listas_palavras_posicoes(caminho_arquivo: str) -> str:
    """
    Lê um arquivo linha a linha e cria um arquivo .py contendo uma matriz:
        matriz = [
            ["palavra1", 1],
            ["palavra2", 2],
            ...
        ]

    Cada ocorrência de palavra é mantida (mesmas palavras repetidas geram linhas distintas).

    Parâmetros:
        caminho_arquivo (str): caminho do arquivo de entrada
            (ex: "mensagens/3_2_1_0_encoded_em_linhas.txt")

    Retorna:
        str: caminho do arquivo gerado (.py).
    """
    # Extrai diretório e nome base
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, _ = os.path.splitext(nome_arquivo)
    caminho_saida = os.path.join(pasta, f"4_{base}.py")

    # Lê as linhas do arquivo (remove linhas vazias)
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    # Gera o conteúdo com matriz ["palavra", posicao]
    conteudo = "matriz = [\n"
    for idx, palavra in enumerate(linhas, start=1):
        palavra_escapada = palavra.replace('"', '\\"')
        conteudo += f'    ["{palavra_escapada}", {idx}],\n'
    conteudo += "]\n"

    # Salva o arquivo gerado
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(conteudo)

    if DEBUG:
        print(f"Arquivo gerado: {caminho_saida}")
        print(f"Total de linhas processadas: {len(linhas)}")

    return caminho_saida









def decodificar_binario_para_ascii(caminho_arquivo: str, compress_whitespace: bool = True) -> tuple[str, str]:
    """
    Processa um arquivo binário e gera dois arquivos numerados sequencialmente:
      1_<arquivo>_em_linhas.txt → linhas de 8 bits
      2_1_<arquivo>_em_linhas.txt → texto ASCII (com espaços trocados por quebras de linha)

    Parâmetros:
        caminho_arquivo (str): caminho do arquivo de entrada (ex: "mensagens/0_encoded.txt")
        compress_whitespace (bool): se True, converte múltiplos espaços/tabs em uma única quebra de linha.

    Retorna:
        (arquivo_em_linhas, arquivo_ascii): caminhos completos dos arquivos gerados.
    """
    # Extrai pasta e nome base
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, ext = os.path.splitext(nome_arquivo)

    # Nomes de saída
    arquivo_em_linhas = os.path.join(pasta, f"1_{base}_em_linhas{ext}")
    arquivo_ascii = os.path.join(pasta, f"2_1_{base}_em_linhas{ext}")

    # Lê o conteúdo original
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        data = f.read()

    # Substitui espaços/tabs/quebras repetidas por uma única quebra de linha
    if compress_whitespace:
        data_linhas = re.sub(r"\s+", "\n", data)
    else:
        data_linhas = data.replace(" ", "\n")

    # === 1ª ETAPA: gerar arquivo com bytes (8 bits por linha) ===
    linhas_processadas = []
    for linha in data_linhas.splitlines():
        binario = linha.strip()
        if not binario:
            continue
        if len(binario) < 8:
            binario = binario.zfill(8)
        linhas_processadas.append(binario)

    # Grava o arquivo 1_..._em_linhas.txt
    with open(arquivo_em_linhas, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_processadas))

    # === 2ª ETAPA: converter para ASCII ===
    ascii_chars = []
    for binario in linhas_processadas:
        try:
            ascii_chars.append(chr(int(binario, 2)))
        except ValueError:
            if DEBUG:
                print(f"Linha inválida ignorada: {binario}")

    # Junta os caracteres ASCII e substitui espaços por quebras de linha
    ascii_texto = "".join(ascii_chars).replace(" ", "\n")

    # Grava o arquivo 2_1_..._em_linhas.txt
    with open(arquivo_ascii, "w", encoding="utf-8") as f:
        f.write(ascii_texto)

    if DEBUG:
        print(f"Arquivo gerado: {arquivo_em_linhas}")
        print(f"Arquivo gerado: {arquivo_ascii}")

    return arquivo_em_linhas, arquivo_ascii





def tratamento_palavras(caminho_arquivo: str) -> str:
    """
    Lê um arquivo de texto e normaliza os tokens, deixando cada palavra/token
    especial em sua própria linha.

    Tokens especiais considerados: '"', "'", '&', ',', '.', '-', '--', '`'

    Regras:
      - O token "--" é reconhecido antes do "-" simples.
      - Todo token (palavra ou caractere especial) é colocado em uma linha separada.
      - Linhas vazias são ignoradas no resultado final.

    Retorna:
      caminho completo do arquivo gerado com prefixo "3_".
    """
    # prepara nomes
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, ext = os.path.splitext(nome_arquivo)
    nome_saida = f"3_{base}{ext}"
    caminho_saida = os.path.join(pasta, nome_saida)

    # lê conteúdo
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        texto = f.read()

    # Expressão regular:
    # - primeiro captura "--"
    # - depois captura qualquer um dos símbolos simples (inclui aspas duplas agora)
    # - ou captura sequências de caracteres que não sejam whitespace nem esses símbolos
    token_pattern = re.compile(r'--|["\'&,\.\-`]|[^\s"\'&,\.\-`]+')

    # encontra todos os tokens na ordem
    tokens = token_pattern.findall(texto)

    # filtra tokens vazios e monta linhas
    linhas = [t for t in tokens if t and t.strip()]

    # grava arquivo de saída (cada token em sua própria linha)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    if DEBUG:
        print(f"Tratamento completo. Arquivo salvo em: {caminho_saida}")
        print(f"Total de tokens: {len(linhas)}")

    return caminho_saida



def analisar_texto_decifrado(arquivo_decifrado: str):
    """
    Analisa o conteúdo de um arquivo de texto decifrado (.txt) e exibe estatísticas:
    - Percentual de palavras reconhecidas (presentes no banco de palavras)
    - Percentual de letras minúsculas (indicando o progresso da decifração)
    """

    # Lê todo o conteúdo do arquivo como uma única string
    with open(arquivo_decifrado, "r", encoding="utf-8") as f:
        data = f.read()

    # Substitui qualquer sequência de espaços, tabulações ou quebras de linha por uma única quebra de linha.
    # Isso garante que cada palavra fique isolada em uma linha.
    data = re.sub(r'\s+', '\n', data)

    # Divide o texto em uma lista de linhas (cada linha contém uma palavra)
    linhas = data.splitlines()

    # Inicializa contadores
    porcentagens = []           # Lista para armazenar o percentual de tradução (caso se queira registrar histórico)
    porcentagem_de_traducao = 0.0
    match_count = 0             # Número de palavras encontradas no banco de palavras
    cont_palavra = 0            # Total de palavras válidas analisadas
    count_minusculas = 0        # Quantidade de letras minúsculas encontradas
    cont_total_letras = 0       # Quantidade total de letras (maiúsculas + minúsculas)

    # Itera sobre cada palavra do texto
    for palavra in linhas:
        # Ignora símbolos isolados e pontuações simples que não são palavras
        if palavra not in {"'", "&", ",", ".", "-", "--", "`"}:
            cont_palavra += 1  # Incrementa o contador de palavras válidas

        # Normaliza a palavra para maiúsculas (para comparação case-insensitive)
        p = palavra.strip().upper()

        # Verifica se a palavra existe no banco de palavras conhecido
        if p in top_words_banco_de_palavras:
            match_count += 1  # Incrementa o contador de palavras reconhecidas

        # Conta letras minúsculas e o total de letras da palavra
        for letra in palavra:
            if letra.islower():      # Verifica se o caractere é uma letra minúscula
                count_minusculas += 1
            cont_total_letras += 1   # Conta todas as letras (independente do caso)

    # Calcula o percentual de tradução (proporção de letras minúsculas)
    porcentagem_de_traducao = count_minusculas / cont_total_letras * 100 if cont_total_letras else 0.0

    # Exibe estatísticas gerais (apenas se o modo DEBUG estiver ativo)
    if DEBUG:
        print(f"MATCHED: {match_count} PALAVRAS")  # Total de palavras encontradas no banco
        print(f"TOTAL DE PALAVRAS VÁLIDAS: {cont_palavra}")  # Total de palavras válidas no texto
        print(f"PORCENTAGEM DE MATCH: {match_count / cont_palavra * 100:.2f}%")  # Percentual de palavras reconhecidas

    # Exibe o percentual de tradução do texto (sempre mostrado)
    #print(f"PORCENTAGEM DE TRADUÇÃO DO TEXTO: {porcentagem_de_traducao:.2f}%")

    # Armazena o resultado na lista de porcentagens (caso seja necessário reutilizar)
    porcentagens.append(f"{porcentagem_de_traducao:.2f}")
    #print(porcentagens)


    return porcentagem_de_traducao

# Exemplo de uso (pode ser removido se for chamado externamente)
# analisar_texto_decifrado("texto_decifrado_em_linhas.txt")