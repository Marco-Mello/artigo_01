"""
funcoes_decodificador.py
"""

import re
import os
from pathlib import Path
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader, module_from_spec
import importlib.util
from collections import Counter, defaultdict
from typing import Dict, Tuple, List, Optional, Set
import shutil

# -------------------------
# CONFIGURAÇÃO GLOBAL
# -------------------------
DEBUG = False  # Se True exibe prints detalhados; se False exibe apenas resumos essenciais

try:
    from top_words_banco_de_palavras import top_words_banco_de_palavras  # type: ignore
except Exception:
    top_words_banco_de_palavras = {}

# -------------------------
# FUNÇÃO DE LIMPEZA
# -------------------------
def limpar_pastas_de_trabalho(pastas: list = None):
    """
    Limpa automaticamente as pastas de trabalho usadas no pipeline.
    Remove todos os arquivos e subpastas de:
      - mensagens/
      - decifrados/
      - mapeamentos/
      - palavrasUsadas/

    Mantém as pastas existentes criadas novamente após a limpeza.
    """
    if pastas is None:
        pastas = ["mensagens", "decifrados", "mapeamentos", "palavrasUsadas"]

    for pasta in pastas:
        p = Path(pasta)
        if p.exists():
            try:
                shutil.rmtree(p)
                if DEBUG:
                    print(f"[DEBUG] Pasta '{p}' limpa com sucesso.")
            except Exception as e:
                print(f"Erro ao limpar a pasta '{p}': {e}")
        # recria pasta vazia
        p.mkdir(parents=True, exist_ok=True)
        if DEBUG:
            print(f"[DEBUG] Pasta '{p}' recriada vazia.")

# -------------------------
# UTILITÁRIOS
# -------------------------
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

def _to_int_safe(v):
    try:
        return int(v)
    except Exception:
        return float('inf')

def _load_matriz_from_py(path: str):
    spec = importlib.util.spec_from_file_location("mod_temp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "matriz", None)

def _write_map_file(map_dict: Dict[str,str], out_path: Path):
    out_path.parent.mkdir(exist_ok=True, parents=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write("final_map = {\n")
        for k, v in map_dict.items():
            f.write(f"    {k!r}: {v!r},\n")
        f.write("}\n")

def _apply_mapping_to_text(text: str, mapping_for_text: Dict[str,str]) -> str:
    for key in sorted(mapping_for_text.keys(), key=lambda s: -len(s)):
        text = text.replace(key, mapping_for_text[key])
    return text

# -------------------------
# PRÉ-PROCESSAMENTO / I/O
# -------------------------
def ler_arquivo_binario(caminho_arquivo: str, destino_dir: str = "mensagens") -> Path:
    src = Path(caminho_arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_arquivo}")

    dest_dir = Path(destino_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "0_encoded.txt"

    try:
        data = src.read_bytes()
        dest_path.write_bytes(data)
    except Exception:
        text = src.read_text(encoding="utf-8")
        dest_path.write_text(text, encoding="utf-8")

    if DEBUG:
        print(f"[DEBUG] Copiado '{caminho_arquivo}' → '{dest_path}'")
    return dest_path

def decodificar_binario_para_ascii(caminho_arquivo: str, compress_whitespace: bool = True) -> tuple[str, str]:
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, ext = os.path.splitext(nome_arquivo)

    arquivo_em_linhas = os.path.join(pasta, f"1_{base}_em_linhas{ext}")
    arquivo_ascii = os.path.join(pasta, f"2_1_{base}_em_linhas{ext}")

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        data = f.read()

    if compress_whitespace:
        data_linhas = re.sub(r"\s+", "\n", data)
    else:
        data_linhas = data.replace(" ", "\n")

    linhas_processadas = []
    for linha in data_linhas.splitlines():
        binario = linha.strip()
        if not binario:
            continue
        if len(binario) < 8:
            binario = binario.zfill(8)
        linhas_processadas.append(binario)

    with open(arquivo_em_linhas, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_processadas))

    ascii_chars = []
    for binario in linhas_processadas:
        try:
            ascii_chars.append(chr(int(binario, 2)))
        except ValueError:
            if DEBUG:
                print(f"[DEBUG] Linha inválida ignorada: {binario}")

    ascii_texto = "".join(ascii_chars).replace(" ", "\n")

    with open(arquivo_ascii, "w", encoding="utf-8") as f:
        f.write(ascii_texto)

    if DEBUG:
        print(f"[DEBUG] Arquivos gerados: '{arquivo_em_linhas}', '{arquivo_ascii}'")
    return arquivo_em_linhas, arquivo_ascii

def tratamento_palavras(caminho_arquivo: str) -> str:
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, ext = os.path.splitext(nome_arquivo)
    nome_saida = f"3_{base}{ext}"
    caminho_saida = os.path.join(pasta, nome_saida)

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        texto = f.read()

    token_pattern = re.compile(r'--|["\'&,\.\-`]|[^\s"\'&,\.\-`]+')
    tokens = token_pattern.findall(texto)
    linhas = [t for t in tokens if t and t.strip()]

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    if DEBUG:
        print(f"[DEBUG] Tratamento concluído. Salvo em: {caminho_saida} (tokens: {len(linhas)})")
    return caminho_saida

def criar_listas_palavras_posicoes(caminho_arquivo: str) -> str:
    pasta, nome_arquivo = os.path.split(caminho_arquivo)
    base, _ = os.path.splitext(nome_arquivo)
    caminho_saida = os.path.join(pasta, f"4_{base}.py")

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    conteudo = "matriz = [\n"
    for idx, palavra in enumerate(linhas, start=1):
        palavra_escapada = palavra.replace('"', '\\"')
        conteudo += f'    ["{palavra_escapada}", {idx}],\n'
    conteudo += "]\n"

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(conteudo)

    if DEBUG:
        print(f"[DEBUG] Arquivo gerado: {caminho_saida} (linhas processadas: {len(linhas)})")
    return caminho_saida

def ordenar_matriz(matriz_ou_arquivo):
    PONTUACOES = {'"', "'", '&', ',', '.', '-', '--', '`'}

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

    ordenada = []
    for comprimento in sorted(grupos_por_len.keys()):
        tokens_do_comprimento = grupos_por_len[comprimento]
        tokens_ordenados = sorted(
            tokens_do_comprimento.keys(),
            key=lambda t: (-occ_counter.get(t, 0), t)
        )
        for token in tokens_ordenados:
            itens_token = tokens_do_comprimento[token]
            itens_token_ordenados = sorted(itens_token, key=lambda it: _to_int_safe(it[1]))
            ordenada.extend(itens_token_ordenados)

    if items_pontuacao:
        grupos_p_pont = defaultdict(list)
        for item in items_pontuacao:
            palavra = "" if item[0] is None else str(item[0])
            grupos_p_pont[palavra].append(item)

        tokens_p_ordenados = sorted(grupos_p_pont.keys(), key=lambda t: (-occ_counter.get(t, 0), t))
        for token in tokens_p_ordenados:
            itens_token = grupos_p_pont[token]
            itens_token_ordenados = sorted(itens_token, key=lambda it: _to_int_safe(it[1]))
            ordenada.extend(itens_token_ordenados)

    if isinstance(matriz_ou_arquivo, (str, Path)):
        nome_arquivo = Path(matriz_ou_arquivo)
        novo_nome = nome_arquivo.parent / f"5_{nome_arquivo.name}"
        with open(novo_nome, "w", encoding="utf-8") as f:
            f.write("matriz = [\n")
            for item in ordenada:
                palavra, numero = item
                palavra_escapada = (
                    str(palavra)
                    .replace("\\", "\\\\")
                    .replace('"', '\\"')
                )
                f.write(f'    ["{palavra_escapada}", {numero}],\n')
            f.write("]\n")
        if DEBUG:
            print(f"[DEBUG] Matriz ordenada salva em: {novo_nome}")
    return ordenada

# -------------------------
# MAPEAMENTO (1/2 letras)
# -------------------------
def map_1_letra(arquivo: str, letra_destino: str = "A") -> Tuple[Dict[str,str], Path, Path]:
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

    if DEBUG:
        print(f"[DEBUG] map_1_letra: mapeado '{primeiro}' → '{letra_destino}'. Map salvo em: {map_path}. Decifrado salvo em: {decifrado_path}")
    return mapping, map_path, decifrado_path

def map_2_letras(arquivo: str, mapping_base: Dict[str,str], duas_letras_token: str, prefix_base: str) -> Tuple[Dict[str,str], Path, Path]:
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")

    if not mapping_base:
        raise ValueError("mapping_base vazio ou None")

    base_src_char, base_dst = next(iter(mapping_base.items()))
    mapped_first_lower = base_dst.lower()

    original_text = src.read_text(encoding="utf-8")
    mapping_base_for_text = {k: v.lower() for k, v in mapping_base.items()}
    temp_text = _apply_mapping_to_text(original_text, mapping_base_for_text)

    pattern = re.compile(r"""(['"])([A-Za-z0-9]{2})\1""")
    encoded_second = None
    matched_token = None
    for m in pattern.finditer(temp_text):
        token = m.group(2)
        if token[0] == mapped_first_lower:
            span_start, span_end = m.span(2)
            orig_token = original_text[span_start:span_end]
            if len(orig_token) == 2:
                encoded_second = orig_token[1]
                matched_token = token
                break
            for mo in pattern.finditer(original_text):
                orig = mo.group(2)
                if len(orig) == 2:
                    if mapping_base.get(orig[0]) == base_dst:
                        encoded_second = orig[1]
                        matched_token = token
                        break
            if encoded_second:
                break
    if encoded_second is None:
        if DEBUG:
            print(f"[DEBUG] Nenhuma palavra de 2 letras iniciando com '{mapped_first_lower}' foi encontrada.")
        else:
            pass
        return None, None, None

    segunda_letra_alvo = duas_letras_token[1]
    mapping_ext = dict(mapping_base)
    mapping_ext[encoded_second] = segunda_letra_alvo

    prefix = prefix_base
    map_path = Path("mapeamentos") / f"{prefix}{duas_letras_token}_final_map.py"
    _write_map_file(mapping_ext, map_path)

    mapping_for_text = {k: v.lower() for k, v in mapping_ext.items()}
    out_text = _apply_mapping_to_text(original_text, mapping_for_text)
    decifrado_path = Path("decifrados") / f"{prefix}{duas_letras_token}_decifrado.py"
    decifrado_path.parent.mkdir(exist_ok=True, parents=True)
    decifrado_path.write_text(out_text, encoding="utf-8")

    if DEBUG:
        print(f"[DEBUG] Mapeamento estendido salvo em {map_path}: {mapping_ext}")
        print(f"[DEBUG] Arquivo decifrado salvo em {decifrado_path} (token encontrado: {matched_token}, encoded_second='{encoded_second}')")
    return mapping_ext, map_path, decifrado_path

# -------------------------
# ANÁLISES / SUGESTÕES
# -------------------------
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
                                  top_words_path: str = "mensagens/top_words_banco_de_palavras.py",
                                  external_used_words: Optional[Set[str]] = None
                                  ) -> List[Tuple[str,int,int,int,float,Optional[str]]]:
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

    results = analyze_by_decreasing_lengths(fonte, mapping_ext, min_len=1, print_report=False)
    if not results:
        return []

    used_words = set()
    external_used = set(external_used_words) if external_used_words else set()
    assigned_by_token = dict()

    def best_candidate_strict_no_reuse(token_display: str, pct: float) -> Optional[str]:
        if pct == 0.0:
            return None

        L = len(token_display)
        known = {i: ch.upper() for i, ch in enumerate(token_display) if ch.islower()}
        candidates = [w for w in top_words.keys() if len(w) == L]
        if not candidates:
            return None

        compat = []
        for cand in candidates:
            if cand in used_words or cand in external_used:
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
    if DEBUG:
        print("\n[DEBUG] Lista de melhores candidatos por ocorrência:")
    for length, token_orig, mapped_count, total, pct, token_display in results:
        if token_display in assigned_by_token:
            best = assigned_by_token[token_display]
        else:
            best = best_candidate_strict_no_reuse(token_display, pct)
            if best is not None:
                assigned_by_token[token_display] = best
                used_words.add(best)
            else:
                best = None

        best_str = best if best is not None else "-"
        if pct < 100.0:
            if DEBUG:
                print(f"  - '{token_display}' (len={length}): {mapped_count}/{total} → {pct:.2f}% | {best_str} (melhor candidato)")
        output.append((token_display, length, mapped_count, total, pct, best if best is not None else None))

    return output

def _extract_tokens_from_file(arquivo: str) -> List[str]:
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")
    text = src.read_text(encoding="utf-8")
    pattern = re.compile(r"""(['"])([A-Za-z0-9_]+)\1""")
    return [m.group(2) for m in pattern.finditer(text)]

def analyze_by_decreasing_lengths(arquivo: str, mapping_ext: Dict[str,str], min_len: int = 1,
                                  print_report: bool = True
                                 ) -> List[Tuple[int, str, int, int, float, str]]:
    src = Path(arquivo)
    if not src.exists():
        if print_report and DEBUG:
            print(f"[DEBUG] Arquivo não encontrado: {arquivo}")
        return []

    text = src.read_text(encoding="utf-8")
    pattern = re.compile(r"""(['"])([A-Za-z0-9_]+)\1""")
    matches = list(pattern.finditer(text))
    if not matches:
        if print_report and DEBUG:
            print("[DEBUG] Nenhum token/string encontrado no arquivo.")
        return []

    occurrences = [(m.group(2), m.start(2), m.end(2)) for m in matches]
    mapped_keys = set(mapping_ext.keys())
    results: List[Tuple[int, str, int, int, float, str]] = []

    for token, sstart, send in occurrences:
        total = len(token)
        if total < min_len:
            continue
        mapped_count = sum(1 for ch in token if ch in mapped_keys)
        pct = (mapped_count / total) * 100.0 if total > 0 else 0.0

        display_chars = []
        for ch in token:
            if ch in mapping_ext and isinstance(mapping_ext[ch], str) and mapping_ext[ch]:
                display_chars.append(mapping_ext[ch].lower())
            else:
                display_chars.append(ch)
        token_display = "".join(display_chars)
        results.append((len(token), token, mapped_count, total, pct, token_display))

    results_sorted = sorted(results, key=lambda x: (-x[4], -x[0], x[1]))

    if print_report and DEBUG:
        print(f"\n[DEBUG] Análise geral (ordenada por maior porcentagem) em {arquivo}:")
        for _, token_orig, mapped_count, total, pct, token_display in results_sorted:
            if pct < 100.0:
                print(f"  - '{token_display}' (len={total}): {mapped_count}/{total} → {pct:.2f}% |")
    return results_sorted

def analyze_longest_words(arquivo: str, mapping_ext: Dict[str,str]) -> List[Tuple[str,int,int,float]]:
    src = Path(arquivo)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {arquivo}")

    text = src.read_text(encoding="utf-8")
    pattern = re.compile(r"""(['"])([A-Za-z0-9]+)\1""")
    tokens = [m.group(2) for m in pattern.finditer(text)]
    if not tokens:
        if DEBUG:
            print("[DEBUG] Nenhum token/string encontrado no arquivo.")
        return []

    max_len = max(len(t) for t in tokens)
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

    if DEBUG:
        print(f"\n[DEBUG] Análise de tokens de comprimento máximo (={max_len}) em {arquivo}:")
        for token, mapped_count, total, pct in results:
            print(f"  - {token!r}: {mapped_count}/{total} letras mapeadas → {pct:.2f}%")
    return results

# -------------------------
# APLICAR CANDIDATOS POR THRESHOLD
# -------------------------
def _find_candidates_from_results(results: List[Tuple[int, str, int, int, float, str]],
                                  top_words: Dict[str,int],
                                  lower_inclusive: float,
                                  upper_exclusive: float,
                                  exclude_words: Optional[Set[str]] = None) -> List[Tuple[int,str,int,int,float,str,str]]:
    selecionados = []
    exclude_words = set(exclude_words) if exclude_words else set()
    top_words_local = _load_top_words("top_words_banco_de_palavras.py")
    for length, token_orig, mapped_count, total, pct, token_display in results:
        if pct >= lower_inclusive and pct < upper_exclusive:
            best_candidate = _best_candidate_for_token_strict_local(token_display, top_words_local)
            if best_candidate and best_candidate in exclude_words:
                L = len(token_display)
                known = {i: ch.upper() for i, ch in enumerate(token_display) if ch.islower()}
                candidates = [w for w in top_words_local.keys() if len(w) == L and w not in exclude_words]
                compat = []
                for cand in candidates:
                    ok = True
                    for i, val in known.items():
                        if cand[i] != val:
                            ok = False
                            break
                    if ok:
                        compat.append(cand)
                if compat:
                    compat.sort(key=lambda w: -top_words_local.get(w, 0))
                    best_candidate = compat[0]
                else:
                    best_candidate = None
            if best_candidate:
                selecionados.append((length, token_orig, mapped_count, total, pct, token_display, best_candidate))
    return selecionados

def apply_candidates_threshold(fonte: str,
                               mapping_ext: Dict[str,str],
                               map_path: Path,
                               dec_path: Path,
                               top_words_path: str,
                               threshold: float,
                               used_words: Optional[Set[str]] = None) -> bool:
    if mapping_ext is None:
        if DEBUG:
            print("[DEBUG] mapping_ext é None — nada a fazer.")
        return False

    try:
        top_words = _load_top_words(top_words_path)
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Erro ao carregar top_words: {e}")
        return False

    resultados = analyze_by_decreasing_lengths(fonte, mapping_ext, min_len=1, print_report=True)
    if not resultados:
        if DEBUG:
            print("[DEBUG] Nenhuma ocorrência encontrada na análise inicial.")
        return False

    candidatos = _find_candidates_from_results(resultados, top_words, threshold, 100.0, exclude_words=used_words)

    if candidatos:
        if DEBUG:
            print(f"\n[DEBUG] Tokens com {threshold:.0f}% <= pct < 100% (candidatos compatíveis):")
            for (length, token_orig, mapped_count, total, pct, token_display, best_candidate) in candidatos:
                print(f"  - '{token_display}' (len={length}): {mapped_count}/{total} → {pct:.2f}% | {best_candidate} (melhor candidato)")
    else:
        if DEBUG:
            print(f"[DEBUG] Nenhum token com {threshold:.0f}% <= pct < 100% encontrado neste subloop (após excluir palavras já usadas).")
        else:
            # Em modo padrão, mostramos apenas mensagem sucinta
            pass
        return False

    changed = False
    newly_used = set()
    for (length, token_orig, mapped_count, total, pct, token_display, best_candidate) in candidatos:
        if used_words and best_candidate in used_words:
            if DEBUG:
                print(f"[DEBUG] Pulando '{best_candidate}': já marcada como usada.")
            continue

        intended_pairs = []
        conflict = False
        conflict_reasons = []

        for i in range(length):
            ch_display = token_display[i]
            if ch_display.islower():
                continue
            encoded_char = token_orig[i]
            target_letter = best_candidate[i].upper()

            existing = mapping_ext.get(encoded_char)
            if existing is not None:
                if existing != target_letter:
                    conflict = True
                    conflict_reasons.append(f"encoded '{encoded_char}' já mapeado para '{existing}' (conflito com '{target_letter}')")
                    break
                else:
                    continue

            inverse_conflict = None
            for enc_k, dec_v in mapping_ext.items():
                if dec_v == target_letter and enc_k != encoded_char:
                    inverse_conflict = enc_k
                    break
            if inverse_conflict is not None:
                conflict = True
                conflict_reasons.append(f"target '{target_letter}' já atribuído a encoded '{inverse_conflict}'")
                break

            intended_pairs.append((encoded_char, target_letter))

        if conflict:
            if DEBUG:
                print(f"[DEBUG] Pulando aplicação de '{best_candidate}' para token '{token_display}' devido a conflito: {'; '.join(conflict_reasons)}")
            continue

        for encoded_char, target_letter in intended_pairs:
            prev = mapping_ext.get(encoded_char)
            mapping_ext[encoded_char] = target_letter
            if DEBUG:
                print(f"[DEBUG] Adicionando mapeamento: {encoded_char!r} -> {target_letter} (anterior: {prev})")
            changed = True

        newly_used.add(best_candidate)

    if used_words is not None:
        used_words.update(newly_used)

    if not changed:
        if DEBUG:
            print("[DEBUG] Nenhuma alteração no mapping_ext (ou todos os candidatos conflitavam).")
        return False

    try:
        _write_map_file(mapping_ext, Path(map_path))
        if DEBUG:
            print(f"[DEBUG] final_map salvo/atualizado em: {Path(map_path)}")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Erro ao salvar final_map: {e}")

    try:
        texto_original = Path(fonte).read_text(encoding="utf-8")
        mapping_for_text = {k: v.lower() for k, v in mapping_ext.items()}
        out_text = _apply_mapping_to_text(texto_original, mapping_for_text)
        Path(dec_path).write_text(out_text, encoding="utf-8")
        if DEBUG:
            print(f"[DEBUG] decifrado reescrito em: {Path(dec_path)}")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Erro ao reescrever decifrado: {e}")

    resultados_novos = analyze_by_decreasing_lengths(fonte, mapping_ext, min_len=1, print_report=True)
    if resultados_novos and DEBUG:
        best_len2, best_orig2, best_mapped_count2, best_total2, best_pct2, best_display2 = resultados_novos[0]
        print(f"\n[DEBUG] (após atualizações) Melhor cobertura geral: comprimento {best_len2}, token '{best_display2}' → {best_pct2:.2f}%")

    return True

def _write_used_words_file(prefix_base: str, token: str, used_words: Set[str]):
    prefix_clean = prefix_base.rstrip("_")
    out_dir = Path("palavrasUsadas")
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{prefix_clean}_{token}_palavras_usadas.txt"
    p = out_dir / fname
    try:
        with p.open("w", encoding="utf-8") as f:
            for w in sorted(used_words):
                f.write(f"{w}\n")
        if DEBUG:
            print(f"[DEBUG] Arquivo de palavras usadas gravado: {p}")
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Erro ao gravar arquivo de palavras usadas '{p}': {e}")
    return p

def handle_subloop_thresholds(fonte: str,
                              mapping_ext: Dict[str,str],
                              map_path: Path,
                              dec_path: Path,
                              token: str,
                              prefix_base: str,
                              top_words_path: str = "top_words_banco_de_palavras.py",
                              thresholds: Tuple[float, ...] = (75.0, 66.0)):
    if mapping_ext is None:
        if DEBUG:
            print("[DEBUG] mapping_ext é None — pulando thresholds.")
        return

    used_words: Set[str] = set()
    for thr in thresholds:
        if DEBUG:
            print(f"\n[DEBUG] Aplicando threshold: >= {thr:.0f}% e < 100%")
        changed = False
        try:
            changed = apply_candidates_threshold(
                fonte=fonte,
                mapping_ext=mapping_ext,
                map_path=Path(map_path),
                dec_path=Path(dec_path),
                top_words_path=top_words_path,
                threshold=thr,
                used_words=used_words
            )
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Erro durante apply_candidates_threshold ({thr}%): {e}")
            changed = False

        if changed and used_words:
            p = _write_used_words_file(prefix_base, token, used_words)
            if DEBUG:
                print(f"[DEBUG] Arquivo de palavras usadas criado/atualizado: {p}")

    if DEBUG:
        print("\n[DEBUG] Executando subloop_action_find_best_word (mapping finalizado para este subloop)...")
    try:
        subloop_action_find_best_word(
            mapping_ext=mapping_ext,
            map_path=Path(map_path),
            dec_path=Path(dec_path),
            fonte=fonte,
            token=token,
            prefix_base=prefix_base,
            top_words_path=top_words_path,
            external_used_words=used_words
        )
    except Exception as e:
        if DEBUG:
            print(f"[DEBUG] Erro em subloop_action_find_best_word: {e}")

# -------------------------
# FALLBACK 3-LETRAS
# -------------------------
def aplicar_3_letras_sequencial_v2(fonte: str,
                                   mapping_base: Optional[Dict[str,str]] = None,
                                   candidate_words: Optional[List[str]] = None,
                                   prefix_base: str = "",  # DEFAULT REMOVIDO: agora vazio por padrão
                                   thresholds: Tuple[float, ...] = (75.0, 66.0, 50.0, 33.0, 25.0, 10.0),
                                   top_words_path: str = "top_words_banco_de_palavras.py",
                                   accumulate_between_candidates: bool = False):
    """
    Processa cada candidate_word repetindo o ciclo (aplicar token -> salvar -> thresholds)
    e imprime métricas após cada decifrado salvo.
    """
    if candidate_words is None:
        candidate_words = ["THE","AND","FOR","WAS","NOT","ARE","HIS","BUT","HAD",
                           "YOU","ONE","ALL","CAN","HER","HAS","WHO"]
    candidate_words = [w.upper() for w in candidate_words if len(w) == 3]

    src = Path(fonte)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {fonte}")

    # load top words for metrics
    try:
        top_words = _load_top_words(top_words_path)
        top_words_set = set(top_words.keys())
    except Exception:
        top_words_set = set()

    # mapping_base copy
    mapping_base = dict(mapping_base) if mapping_base else {}

    # resultado por candidate
    per_candidate = {}

    # mapping acumulado global (se accumulate_between_candidates True)
    global_mapping = dict(mapping_base) if accumulate_between_candidates else None

    from collections import Counter

    def _can_apply_pairs_for_token(token_orig: str, candidate: str, current_map: Dict[str,str]):
        pairs = []
        for i in range(3):
            enc = token_orig[i]
            tgt = candidate[i].upper()
            existing = current_map.get(enc)
            if existing is not None:
                if existing != tgt:
                    return False, [], f"encoded '{enc}' já mapeado para '{existing}' (conflito com '{tgt}')"
                else:
                    continue
            # não permitir que tgt já esteja vinculado a outro encoded distinto
            for ek, ev in current_map.items():
                if ev == tgt and ek != enc:
                    return False, [], f"target '{tgt}' já atribuído a encoded '{ek}'"
            pairs.append((enc, tgt))
        if not pairs:
            return False, [], "token já completamente compatível (sem novos pares)"
        return True, pairs, ""

    def _make_map_dec_paths(prefix: str, suffix_tag: str):
        """
        Retorna (map_path, dec_path) montando os nomes corretamente dependendo de prefix (possivelmente vazio).
        """
        if prefix:
            map_name = f"{prefix}_{suffix_tag}_final_map.py"
            dec_name = f"{prefix}_{suffix_tag}_decifrado.py"
        else:
            map_name = f"{suffix_tag}_final_map.py"
            dec_name = f"{suffix_tag}_decifrado.py"
        return Path("mapeamentos") / map_name, Path("decifrados") / dec_name

    def _save_step_and_print_stats(src_path: Path, mapping_now: Dict[str,str], suffix_tag: str, prefix_raw: str):
        # prefix_raw é prefix_base sem trailing "_"
        map_path, dec_path = _make_map_dec_paths(prefix_raw, suffix_tag)
        _write_map_file(mapping_now, map_path)

        texto_original = src_path.read_text(encoding="utf-8")
        mapping_for_text = {k: v.lower() for k, v in mapping_now.items()}
        out_text = _apply_mapping_to_text(texto_original, mapping_for_text)
        dec_path.parent.mkdir(parents=True, exist_ok=True)
        dec_path.write_text(out_text, encoding="utf-8")

        # imprime apenas a linha resumo (sempre)
        _print_decifrado_stats(dec_path, top_words_set)
        if DEBUG:
            print(f"[DEBUG] final_map salvo: {map_path}")
            print(f"[DEBUG] decifrado salvo: {dec_path}")
        return map_path, dec_path

    def _print_decifrado_stats(dec_path: Path, top_words_set: set):
        text = dec_path.read_text(encoding="utf-8")
        palavras = re.findall(r"[A-Za-z]+", text)
        total_palavras = len(palavras)
        encontradas = sum(1 for p in palavras if p.upper() in top_words_set) if total_palavras else 0
        pct_palavras = (encontradas / total_palavras * 100.0) if total_palavras else 0.0
        letras = re.findall(r"[A-Za-z]", text)
        total_letras = len(letras)
        minusculas = sum(1 for ch in letras if ch.islower()) if total_letras else 0
        pct_traducao = (minusculas / total_letras * 100.0) if total_letras else 0.0

    # prefix clean (sem underscore)
    prefix_clean = prefix_base.rstrip("_")

    # loop por cada candidate
    for cand in candidate_words:
        if DEBUG:
            print(f"\n[DEBUG] === CANDIDATE 3-LETRAS: {cand} ===")
        if accumulate_between_candidates:
            mapping_ext = dict(global_mapping)
        else:
            mapping_ext = dict(mapping_base)

        applied_tokens = []
        map_paths = []
        dec_paths = []
        step_counter = 0
        any_applied_for_candidate = False

        # repetir enquanto houver ocorrências aplicáveis
        while True:
            resultados = analyze_by_decreasing_lengths(fonte, mapping_ext, min_len=3, print_report=False)
            occs = [(length, token_orig, mapped_count, total, pct, token_display)
                    for (length, token_orig, mapped_count, total, pct, token_display) in resultados
                    if length == 3 and pct < 100.0]

            if not occs:
                break

            token_list = [token_orig for (_, token_orig, _, _, _, _) in occs]
            counts = Counter(token_list)
            apply_candidates = []
            for idx, (length, token_orig, mapped_count, total, pct, token_display) in enumerate(occs):
                compatible = True
                for i, ch in enumerate(token_display):
                    if ch.islower() and ch != cand[i].lower():
                        compatible = False
                        break
                if not compatible:
                    continue
                ok, pairs, reason = _can_apply_pairs_for_token(token_orig, cand, mapping_ext)
                if not ok:
                    continue
                apply_candidates.append((token_orig, pairs, counts[token_orig], idx))

            if not apply_candidates:
                break

            # escolher com maior frequência
            apply_candidates.sort(key=lambda x: (-x[2], x[3]))
            token_to_apply, pairs_to_apply, _, _ = apply_candidates[0]

            # aplicar pares
            for enc, tgt in pairs_to_apply:
                prev = mapping_ext.get(enc)
                mapping_ext[enc] = tgt
                if DEBUG:
                    print(f"[DEBUG] Aplicado (token {token_to_apply}): {enc!r} -> {tgt} (anterior: {prev})")

            step_counter += 1
            applied_tokens.append(token_to_apply)
            any_applied_for_candidate = True

            # salvar estado e imprimir métricas (sufixo identifica candidate+step)
            suf = f"{cand}_step{step_counter}"
            map_path, dec_path = _save_step_and_print_stats(src, mapping_ext, suf, prefix_clean)
            map_paths.append(map_path)
            dec_paths.append(dec_path)

            # executar thresholds (reutiliza lógica existente)
            try:
                handle_subloop_thresholds(
                    fonte=fonte,
                    mapping_ext=mapping_ext,
                    map_path=map_path,
                    dec_path=dec_path,
                    token=cand,
                    prefix_base=prefix_base,
                    top_words_path=top_words_path,
                    thresholds=thresholds
                )
            except Exception as e:
                if DEBUG:
                    print(f"[DEBUG] Erro em handle_subloop_thresholds para {cand}: {e}")

            # continuar loop
            continue

        # resumo por candidate
        if any_applied_for_candidate:
            if DEBUG:
                print(f"[DEBUG] Aplicações totais para {cand}: {len(applied_tokens)}")
        else:
            if DEBUG:
                print(f"[DEBUG] Nenhuma aplicação possível para {cand}.")
        per_candidate[cand] = {
            "mapping_final": dict(mapping_ext),
            "applied_tokens": applied_tokens,
            "map_paths": map_paths,
            "dec_paths": dec_paths
        }
        if accumulate_between_candidates:
            global_mapping = dict(mapping_ext)

    return {
        "per_candidate": per_candidate,
        "global_final_mapping": (global_mapping if accumulate_between_candidates else None)
    }


def aplicar_3_letras_sem_subloop(fonte: str,
                                 mapping_base: Dict[str,str],
                                 candidate_words: List[str],
                                 prefix_base: str = "",  # agora default vazio
                                 top_words_path: str = "top_words_banco_de_palavras.py"):
    candidate_words = [w.upper() for w in candidate_words if len(w) == 3]
    if not candidate_words:
        return None, None, None, []

    src = Path(fonte)
    if not src.exists():
        raise FileNotFoundError(f"Arquivo fonte não encontrado: {fonte}")

    mapping_ext = dict(mapping_base) if mapping_base else {}
    used_words = set()
    original_text = src.read_text(encoding="utf-8")
    pattern = re.compile(r"""(['"])([A-Za-z]{3})\1""")
    matches = list(pattern.finditer(original_text))
    if not matches:
        return None, None, None, []

    def token_display_from_token(token: str, mapping: Dict[str,str]) -> str:
        chars = []
        for ch in token:
            if ch in mapping and isinstance(mapping[ch], str) and mapping[ch]:
                chars.append(mapping[ch].lower())
            else:
                chars.append(ch)
        return "".join(chars)

    def can_apply_word_for_token(token_orig: str, candidate: str, current_map: Dict[str,str]) -> Tuple[bool, List[Tuple[str,str]], str]:
        pairs = []
        for i in range(3):
            enc = token_orig[i]
            tgt = candidate[i].upper()
            existing = current_map.get(enc)
            if existing is not None:
                if existing != tgt:
                    return False, [], f"encoded '{enc}' já mapeado para '{existing}' (conflito com '{tgt}')"
                else:
                    continue
            for k, v in current_map.items():
                if v == tgt and k != enc:
                    return False, [], f"target '{tgt}' já atribuído a encoded '{k}'"
            pairs.append((enc, tgt))
        return True, pairs, ""

    words_applied = []

    for m in matches:
        token_orig = m.group(2)
        token_disp = token_display_from_token(token_orig, mapping_ext)
        applied_this_occurrence = False
        for cand in candidate_words:
            if cand in used_words:
                continue
            ok, pairs, reason = can_apply_word_for_token(token_orig, cand, mapping_ext)
            if not ok:
                continue
            for enc, tgt in pairs:
                mapping_ext[enc] = tgt
            used_words.add(cand)
            words_applied.append((token_orig, cand))
            applied_this_occurrence = True
            break

    if not words_applied:
        return None, None, None, []

    # nomeação de arquivos respeitando prefix vazio
    prefix_clean = prefix_base.rstrip("_")
    if prefix_clean:
        map_path = Path("mapeamentos") / f"{prefix_clean}_3letters_final_map.py"
        dec_path = Path("decifrados") / f"{prefix_clean}_3letters_decifrado.py"
    else:
        map_path = Path("mapeamentos") / f"3letters_final_map.py"
        dec_path = Path("decifrados") / f"3letters_decifrado.py"

    _write_map_file(mapping_ext, map_path)

    mapping_for_text = {k: v.lower() for k, v in mapping_ext.items()}
    out_text = _apply_mapping_to_text(original_text, mapping_for_text)
    dec_path.parent.mkdir(exist_ok=True, parents=True)
    dec_path.write_text(out_text, encoding="utf-8")

    if DEBUG:
        print(f"[DEBUG] Aplicações 3-letras para prefix '{prefix_clean}':")
        for tok, cand in words_applied:
            print(f"[DEBUG]  - token '{tok}' -> {cand}")
        print(f"[DEBUG] Mapeamento salvo em: {map_path}")
        print(f"[DEBUG] Decifrado salvo em: {dec_path}")
    else:
        # impressão resumida (linha por arquivo)
        try:
            top_words_set = set(_load_top_words(top_words_path).keys()) if top_words_path else set()
            text = dec_path.read_text(encoding="utf-8")
            palavras = re.findall(r"[A-Za-z]+", text)
            total_palavras = len(palavras)
            encontradas = sum(1 for p in palavras if p.upper() in top_words_set) if total_palavras else 0
            pct_palavras = (encontradas / total_palavras * 100.0) if total_palavras else 0.0
            letras = re.findall(r"[A-Za-z]", text)
            total_letras = len(letras)
            minusculas = sum(1 for ch in letras if ch.islower()) if total_letras else 0
            pct_traducao = (minusculas / total_letras * 100.0) if total_letras else 0.0
        except Exception:
            pass

    return mapping_ext, map_path, dec_path, words_applied


# -------------------------
# ORQUESTRAÇÃO PRINCIPAL (1 letra + subloops)
# -------------------------
def executar_pipeline_decifrado(fonte: str,
                                top_words_path: str,
                                thresholds_to_run: tuple,
                                uma_letra: list = ["A", "I"],
                                duas_letras_A: list = ["AS", "AT", "AN", "AM"],
                                duas_letras_I: list = ["IN", "IS", "IT", "IF"]) -> bool:
    sucesso_geral = False
    for letra in uma_letra:
        if DEBUG:
            print(f"\n[DEBUG] === Passo 1: letra {letra} ===")
        mapping1, map1_path, dec1 = None, None, None
        try:
            mapping1, map1_path, dec1 = map_1_letra(fonte, letra_destino=letra)
        except Exception as e:
            if DEBUG:
                print(f"[DEBUG] Erro em map_1_letra para {letra}: {e}")
            mapping1 = None

        if mapping1 is None:
            continue

        duas = duas_letras_A if letra == "A" else duas_letras_I
        prefix_base = f"{letra}_"

        for token in duas:
            if DEBUG:
                print(f"[DEBUG]  --- Subloop token: {token} ---")
            mapping_ext, map2_path, dec2 = map_2_letras(fonte, mapping1, token, prefix_base)
            if not mapping_ext:
                if DEBUG:
                    print(f"[DEBUG]  >>> Nenhum mapeamento estendido para token {token}.")
                continue

            sucesso_geral = True
            handle_subloop_thresholds(
                fonte=fonte,
                mapping_ext=mapping_ext,
                map_path=map2_path,
                dec_path=dec2,
                token=token,
                prefix_base=prefix_base,
                top_words_path=top_words_path,
                thresholds=thresholds_to_run
            )

    if not sucesso_geral:
        if DEBUG:
            print("\n[DEBUG] Nenhum mapeamento válido foi encontrado em nenhum subloop!")
        return False

    if DEBUG:
        print("\n[DEBUG] Pelo menos um mapeamento foi encontrado e processado com sucesso.")
    return True

# -------------------------
# FUNÇÕES DE RELATÓRIO / PÓS-PROCESSAMENTO
# -------------------------
def analisar_decifrados_completo(top_words_path: str = "top_words_banco_de_palavras.py",
                                 decifrados_dir: str = "decifrados",
                                 print_report: bool = True):
    """
    Imprime apenas os arquivos agrupados por etapa (1 letra, 2 letras, 3 letras)
    e depois mostra o arquivo escolhido (melhor).

    """
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    p_dec = Path(decifrados_dir)
    if not p_dec.exists() or not p_dec.is_dir():
        raise FileNotFoundError(f"Pasta de decifrados não encontrada: {decifrados_dir}")

    # carrega top_words (para métricas)
    top_words = _load_top_words(top_words_path)
    top_words_set = set(top_words.keys())

    resultados = {}

    for fpath in sorted(p_dec.glob("*.py")):
        text = fpath.read_text(encoding="utf-8")

        palavras = re.findall(r"[A-Za-z]+", text)
        total_palavras = len(palavras)
        encontradas = sum(1 for p in palavras if p.upper() in top_words_set)
        pct_palavras = (encontradas / total_palavras * 100.0) if total_palavras else 0.0

        letras = re.findall(r"[A-Za-z]", text)
        total_letras = len(letras)
        minusculas = sum(1 for ch in letras if ch.islower())
        pct_traducao = (minusculas / total_letras * 100.0) if total_letras else 0.0

        resultados[str(fpath)] = {
            "nome": fpath.name,
            "total_palavras": total_palavras,
            "encontradas": encontradas,
            "pct_palavras": pct_palavras,
            "total_letras": total_letras,
            "minusculas": minusculas,
            "pct_traducao": pct_traducao,
        }

    if not resultados:
        print("Nenhum arquivo encontrado em 'decifrados/'.")
        return {}

    # Determina o melhor (mesma regra que antes)
    melhor = max(
        resultados.values(),
        key=lambda x: (x["pct_traducao"], x["pct_palavras"])
    )

    # --- Funções utilitárias para detectar etapa via nome de arquivo ---
    def _normalize_name(nome: str) -> str:
        """Remove prefixos/sufixos previsíveis e normaliza para A_AT, THE, 3letters, etc."""
        s = nome
        s = re.sub(r"^3_", "", s, flags=re.IGNORECASE)             # remove leading 3_ se existir
        s = re.sub(r"_step\d+", "", s, flags=re.IGNORECASE)       # remove _stepN
        s = re.sub(r"_decifrado\.py$", "", s, flags=re.IGNORECASE)
        s = re.sub(r"_final_map\.py$", "", s, flags=re.IGNORECASE)
        return s

    def _letters_tokens_from_name(nome_normalizado: str) -> List[str]:
        """Retorna lista de tokens de letras (somente A-Z) encontrados no nome."""
        parts = re.split(r"[_\-\s]+", nome_normalizado)
        tokens = []
        for p in parts:
            # manter apenas blocos que contenham apenas letras A-Z
            m = re.fullmatch(r"[A-Za-z]+", p)
            if m:
                tokens.append(p.upper())
        return tokens

    def _determine_stage_by_name(nome_arquivo: str) -> int:
        """
        Retorna 1, 2 ou 3 baseado em heurísticas:
         - se houver um token de 2 letras e houver também um token de 1 letra -> etapa 2 (ex: A_AT)
         - se houver token de comprimento 1 e nenhum token de 2 -> etapa 1 (ex: A)
         - se houver token de comprimento 3 (THE, AND, etc) -> etapa 3
         - fallback: se soma total de letras for 1 -> 1, 2 -> 2, >=3 -> 3
        """
        norm = _normalize_name(nome_arquivo)
        tokens = _letters_tokens_from_name(norm)
        if not tokens:
            # fallback simples baseado no nome sem letras
            total_letters = len(re.findall(r"[A-Za-z]", nome_arquivo))
            if total_letters <= 1:
                return 1
            if total_letters == 2:
                return 2
            return 3

        # Prefira detectar padrão "X_YY" (1-letter then 2-letter) => etapa 2
        has_len1 = any(len(t) == 1 for t in tokens)
        has_len2 = any(len(t) == 2 for t in tokens)
        has_len3 = any(len(t) == 3 for t in tokens)

        if has_len1 and has_len2:
            return 2
        if has_len1 and not has_len2 and not has_len3:
            return 1
        if has_len3 and not has_len1:
            return 3

        # Caso ambíguo: usar fallback pela maior ocorrência de tamanho
        lengths = [len(t) for t in tokens]
        most_common_len = max(set(lengths), key=lengths.count)
        if most_common_len == 1:
            return 1
        if most_common_len == 2:
            return 2
        return 3

    # --- Agrupar por etapa 1,2,3 ---
    groups = {1: [], 2: [], 3: []}
    others = []

    for path_str, info in resultados.items():
        nome = info["nome"]
        etapa = _determine_stage_by_name(nome)
        if etapa in groups:
            groups[etapa].append((nome, info))
        else:
            others.append((nome, info))

    # Impressão agrupada — só etapas 1,2,3 (se existirem)
    if print_report:
        if groups[1]:
            print("\n===== Etapa 1 (palavras de 1 letra) =====")
            for nome, info in groups[1]:
                print(f"{nome:<35} | Qtd. encontradas: {info['pct_palavras']:6.2f}% | Percentual do texto traduzido: {info['pct_traducao']:6.2f}%")
        if groups[2]:
            print("\n===== Etapa 2 (palavras de 2 letras) =====")
            for nome, info in groups[2]:
                print(f"{nome:<35} | Qtd. encontradas: {info['pct_palavras']:6.2f}% | Percentual do texto traduzido: {info['pct_traducao']:6.2f}%")
        if groups[3]:
            print("\n===== Etapa 3 (palavras de 3 letras) =====")
            for nome, info in groups[3]:
                print(f"{nome:<35} | Qtd. encontradas: {info['pct_palavras']:6.2f}% | Percentual do texto traduzido: {info['pct_traducao']:6.2f}%")

        # Por fim, imprime o escolhido (melhor)
        nome_melhor_limpo = re.sub(r"^3_", "", melhor["nome"])
        nome_melhor_limpo = re.sub(r"_step\d+", "", nome_melhor_limpo)
        print(f"\n→ Arquivo com maior progresso: {YELLOW}{nome_melhor_limpo}{RESET}")

    return resultados


def imprimir_melhor_texto(decifrados_dir: str = "decifrados",
                          top_words_path: str = "top_words_banco_de_palavras.py",
                          out_filename: str = "encoded_decifrado.txt",
                          print_report: bool = True):
    """
    Seleciona o arquivo .py mais traduzido, imprime:
      - mapeamentos encontrados em mapeamentos/*.py (final_map)
      - letras decifradas (lista) e letras faltantes (lista)
    e então gera e salva o texto final ordenado em `out_filename`.

    Retorna: (out_path, melhor_path)
    """
    p_dec = Path(decifrados_dir)
    if not p_dec.exists() or not p_dec.is_dir():
        raise FileNotFoundError(f"Pasta de decifrados não encontrada: {decifrados_dir}")

    # --- Determina o melhor arquivo por pct_traducao (desempate por pct_palavras) ---
    top_words = _load_top_words(top_words_path)
    top_words_set = set(top_words.keys())
    resultados = {}

    for fpath in sorted(p_dec.glob("*.py")):
        text = fpath.read_text(encoding="utf-8")
        palavras = re.findall(r"[A-Za-z]+", text)
        total_palavras = len(palavras)
        encontradas = sum(1 for p in palavras if p.upper() in top_words_set)
        pct_palavras = (encontradas / total_palavras * 100.0) if total_palavras else 0.0

        letras = re.findall(r"[A-Za-z]", text)
        total_letras = len(letras)
        minusculas = sum(1 for ch in letras if ch.islower())
        pct_traducao = (minusculas / total_letras * 100.0) if total_letras else 0.0

        resultados[fpath] = (pct_traducao, pct_palavras)

    if not resultados:
        raise RuntimeError("Nenhum arquivo .py encontrado em 'decifrados/'.")

    melhor_path = max(resultados.keys(), key=lambda k: resultados[k])

    # --- Extrai pares ["palavra", pos] do melhor arquivo ---
    matriz = None
    try:
        spec = importlib.util.spec_from_file_location("decifrado_mod_temp", str(melhor_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        matriz = getattr(mod, "matriz", None)
    except Exception:
        matriz = None

    entries = []
    if matriz and isinstance(matriz, (list, tuple)):
        for item in matriz:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                try:
                    pos = int(item[1])
                    word = str(item[0])
                    entries.append((pos, word))
                except Exception:
                    continue
    else:
        # fallback regex: captura ["word", 123]
        text = melhor_path.read_text(encoding="utf-8")
        pattern = re.compile(r"""\[\s*(['"])(.*?)\1\s*,\s*([0-9]+)\s*\]""", re.DOTALL)
        for m in pattern.finditer(text):
            word = m.group(2)
            pos = int(m.group(3))
            entries.append((pos, word))

    if not entries:
        raise RuntimeError(f"Não foi possível extrair pares [palavra, posição] do arquivo {melhor_path}")

    # --- Ordena por posição ascendente e monta o texto final ---
    entries_sorted = sorted(entries, key=lambda x: x[0])
    words_in_order = [w for _, w in entries_sorted]
    texto_final = " ".join(words_in_order)

    # --- Tenta carregar mapeamentos (final_map) de mapeamentos/*.py ---
    combined_map: Dict[str, str] = {}
    p_maps = Path("mapeamentos")
    if p_maps.exists() and p_maps.is_dir():
        for mp in sorted(p_maps.glob("*.py")):
            try:
                specm = importlib.util.spec_from_file_location(f"map_mod_{mp.stem}", str(mp))
                modm = importlib.util.module_from_spec(specm)
                specm.loader.exec_module(modm)
                fm = getattr(modm, "final_map", None)
                if isinstance(fm, dict):
                    # combinamos: arquivos posteriores sobrescrevem chaves anteriores
                    for k, v in fm.items():
                        if isinstance(k, str) and isinstance(v, str) and v:
                            combined_map[k] = v.upper()
            except Exception:
                # ignora arquivos que não carregam
                continue

    # --- Letras mapeadas / faltantes ---
    ALFABETO = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

   
    letras_mapeadas_por_map = set(v.upper() for v in combined_map.values() if isinstance(v, str) and v.strip())
    letras_mapeadas_por_texto = set(ch.upper() for ch in texto_final if ch.islower())

    # união das fontes para definir letras mapeadas conhecidas
    letras_mapeadas = letras_mapeadas_por_map.union(letras_mapeadas_por_texto)
    letras_faltantes = sorted(ALFABETO - letras_mapeadas)

    
    print("\n================== MAPA DE LETRAS ==================")
    # imprime pares mapeados (encoded -> decoded) se existirem
    if combined_map:
        print("\nMapeamentos conhecidos (encoded -> decoded):")
        # ordena por decoded letra para legibilidade
        for enc, dec in sorted(combined_map.items(), key=lambda x: (x[1], x[0])):
            print(f"  {enc!r} -> {dec}")
        print()
    else:
        print("\nNenhum arquivo de mapeamento encontrado em 'mapeamentos/' (ou não contém 'final_map').\n")

    # imprime letras mapeadas e faltantes com contagens
    print(f"Letras já decifradas ({len(letras_mapeadas)}): {', '.join(sorted(letras_mapeadas)) if letras_mapeadas else '(nenhuma)'}")
    print(f"Letras faltantes ({len(letras_faltantes)}): {', '.join(letras_faltantes) if letras_faltantes else '(nenhuma)'}")
    print("====================================================\n")

    # --- Imprime e salva o texto final (somente palavras em sequência separadas por espaço) ---
    if print_report:
        print(texto_final)

    out_path = Path(out_filename)
    out_path.write_text(texto_final, encoding="utf-8")
    if DEBUG:
        print(f"[DEBUG] Texto final salvo em: {out_path} (arquivo escolhido: {melhor_path})")

    return out_path, melhor_path


# -------------------------
# WRAPPER: executar_fallback_3_letras
# -------------------------
def executar_fallback_3_letras(fonte: str,
                               top_words_path: str,
                               thresholds_to_run: Tuple[float, ...],
                               mapping_base: Optional[Dict[str, str]] = None,
                               accumulate_between_candidates: bool = False):
    """
    Executa automaticamente o fallback de 3 letras:
      - Tenta aplicar sequencialmente as palavras de 3 letras mais comuns;
      - Detecta o formato do retorno (legacy/applied ou per_candidate);
      - Exibe um resumo amigável com as aplicações encontradas.

    Retorna o dicionário resultado retornado pela função aplicar_3_letras_sequencial_v2.
    """
    

    tres_palavras = [
        "THE", "AND", "FOR", "WAS", "NOT", "ARE", "HIS", "BUT",
        "HAD", "YOU", "ONE", "ALL", "CAN", "HER", "HAS", "WHO"
    ]

    resultado_fallback = aplicar_3_letras_sequencial_v2(
        fonte=fonte,
        mapping_base=mapping_base or {},
        candidate_words=tres_palavras,
        thresholds=thresholds_to_run,
        top_words_path=top_words_path,
        accumulate_between_candidates=accumulate_between_candidates
    )

    # --- Compatibilidade: se a função antiga retornou 'applied', use-a ---
    if isinstance(resultado_fallback, dict) and "applied" in resultado_fallback:
        applied = resultado_fallback.get("applied", {})
        any_applied = any(applied.get(w) for w in applied)
        if any_applied:
            
            for palavra, tokens in applied.items():
                if tokens:
                    print(f"  - {palavra}: {len(tokens)} aplicações (tokens: {', '.join(tokens)})")
        else:
            pass
        return resultado_fallback

    # --- Novo formato: per_candidate ---
    elif isinstance(resultado_fallback, dict) and "per_candidate" in resultado_fallback:
        per_candidate = resultado_fallback["per_candidate"]
        any_applied = any(info.get("applied_tokens") for info in per_candidate.values())

        if any_applied:
            # modo silencioso por padrão (imprime apenas linhas resumo dos arquivos criados)
            for palavra, info in per_candidate.items():
                applied_tokens = info.get("applied_tokens", [])
                # em modo não-DEBUG, não imprimimos a lista detalhada por candidate
                # mas as linhas resumo dos arquivos já foram escritas por _save_step_and_print_stats
                if DEBUG:
                    if applied_tokens:
                        print(f"[DEBUG] {palavra}: {len(applied_tokens)} aplicações (tokens: {', '.join(applied_tokens)})")
        else:
            # se nenhum aplicado, informa sucintamente
            if DEBUG:
                print("[DEBUG] Nenhuma aplicação foi encontrada no fallback de 3 letras.")
        return resultado_fallback

    else:
        print("Fallback retornou um formato inesperado:")
        print(resultado_fallback)
        return resultado_fallback
