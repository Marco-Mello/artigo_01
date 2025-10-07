# -*- coding: utf-8 -*-
"""
corrigir_palavras.py

Regras:
- Processa palavras de message_NEW.txt priorizando as mais longas.
- Usa update_map de update_dictionary.py (não sobrescreve mapeamentos existentes).
- Usa english_rank de top_words.py (rank 1 = mais frequente).
- Só compara candidatos com mesmo tamanho.
- Compatibilidade >= 50% (inclui igual).
- Não permite duas letras diferentes apontarem para o mesmo destino (mantém o primeiro).
- Confirmações:
    - linha em branco em message_NEW.txt
    - escreve palavra na mesma linha em message_NEW_FINAL.txt (se ainda estiver vazia)
- Atualiza update_dictionary.py com uma letra por linha.
- Imprime relatório completo das atualizações no dicionário.
"""
import re
from collections import defaultdict
from update_dictionary import update_map
from top_words import english_rank

MESSAGE_FILE = "message_NEW.txt"
FINAL_FILE = "message_NEW_FINAL.txt"
UPDATE_DICT_FILE = "update_dictionary.py"
MIN_COMPATIBILITY = 50.0  # compatibilidade mínima (>=)

def apply_letter_map(word, letter_map):
    return "".join(letter_map.get(ch, ch) for ch in word)

def compatibility_score(a, b):
    if len(a) != len(b):
        return 0.0
    if not a:
        return 100.0
    matches = sum(1 for i in range(len(a)) if a[i] == b[i])
    return (matches / len(a)) * 100.0

def choose_best_candidate_same_length(word, candidates):
    best = None
    best_score = -1.0
    best_rank = float("inf")  # menor rank = mais frequente
    for cand, rank in candidates:
        if len(cand) != len(word):
            continue
        score = compatibility_score(word, cand)
        if score > best_score or (score == best_score and rank < best_rank):
            best, best_score, best_rank = cand, score, rank
    return best, best_score, best_rank

def find_existing_source_for_target(target, map_dict):
    for src, dst in map_dict.items():
        if dst == target:
            return src
    return None

def update_update_dictionary_file(path, new_map):
    """Atualiza update_dictionary.py escrevendo update_map com uma linha por item."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    # monta bloco formatado
    lines = ["update_map = {"]
    for k, v in sorted(new_map.items()):
        lines.append(f"    {repr(k)}: {repr(v)},")
    lines.append("}")
    dict_block = "\n".join(lines)

    # substitui bloco existente ou acrescenta no final
    new_content, n_subs = re.subn(
        r"update_map\s*=\s*\{.*?\}",
        dict_block,
        content,
        flags=re.DOTALL
    )
    if n_subs == 0:
        header = "# -*- coding: utf-8 -*-\n# Dicionário gerado automaticamente\n\n"
        new_content = (header + dict_block + "\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

def main():
    # carrega dados
    update_map_local = {k.upper(): v.upper() for k, v in update_map.items()}
    rank_dict = {k.upper(): int(v) for k, v in english_rank.items()}
    candidates = list(rank_dict.items())

    substituted_count = 0
    added_mappings = defaultdict(int)
    skipped_due_to_target_taken = defaultdict(int)
    conflicts = defaultdict(int)
    moved_words = []  # (palavra, score, linha)

    # lê arquivos
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    try:
        with open(FINAL_FILE, "r", encoding="utf-8") as f:
            final_lines = f.read().splitlines()
    except FileNotFoundError:
        final_lines = [""] * len(lines)

    if len(final_lines) < len(lines):
        final_lines.extend([""] * (len(lines) - len(final_lines)))

    out_message_lines = [None] * len(lines)
    idxs_sorted = sorted(range(len(lines)), key=lambda i: len(lines[i].strip()), reverse=True)

    for idx in idxs_sorted:
        original = lines[idx].strip()
        if not original:
            out_message_lines[idx] = ""
            continue

        if idx < len(final_lines) and final_lines[idx].strip():
            out_message_lines[idx] = ""
            continue

        word = original.upper()
        word_after_map = apply_letter_map(word, update_map_local)
        best_cand, best_score, best_rank = choose_best_candidate_same_length(word_after_map, candidates)

        if best_cand and best_score >= MIN_COMPATIBILITY:
            for i in range(len(word_after_map)):
                a = word_after_map[i]
                b = best_cand[i]
                if a == b:
                    continue
                if a in update_map_local:
                    if update_map_local[a] != b:
                        conflicts[(a, update_map_local[a], b)] += 1
                    continue
                existing_src = find_existing_source_for_target(b, update_map_local)
                if existing_src and existing_src != a:
                    skipped_due_to_target_taken[(a, b, existing_src)] += 1
                    continue
                update_map_local[a] = b
                added_mappings[(a, b)] += 1

            substituted_count += 1
            moved_words.append((best_cand, best_score, idx))
            out_message_lines[idx] = ""
            if not final_lines[idx].strip():
                final_lines[idx] = best_cand
        else:
            out_message_lines[idx] = word_after_map

    # grava arquivos
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        for ln in out_message_lines:
            f.write(ln + "\n")
    with open(FINAL_FILE, "w", encoding="utf-8") as f:
        for ln in final_lines:
            f.write(ln + "\n")

    final_map = dict(sorted(update_map_local.items()))
    update_update_dictionary_file(UPDATE_DICT_FILE, final_map)

    # --- Relatório principal ---
    print("✅ Processamento concluído.")
    print(f"Palavras movidas para {FINAL_FILE}: {substituted_count}")
    if moved_words:
        print("\n📦 Palavras movidas (com compatibilidade e linha):")
        for w, score, idx in moved_words:
            print(f"  - {w} ({score:.2f}%) — linha {idx+1}")

    if added_mappings:
        print("\n🔤 Novos mapeamentos adicionados:")
        for (a, b), cnt in sorted(added_mappings.items()):
            print(f"  {a} -> {b} ({cnt}x)")
    if skipped_due_to_target_taken:
        print("\n⚠️ Mapeamentos ignorados (target já ocupado):")
        for (a, b, existing_src), cnt in skipped_due_to_target_taken.items():
            print(f"  {a} -> {b} (já usado por {existing_src}) [{cnt}x]")
    if conflicts:
        print("\n⚔️ Conflitos (origem já mapeada diferente):")
        for (a, existing, sugerido), cnt in conflicts.items():
            print(f"  {a}: existente {existing}, sugerido {sugerido} ({cnt}x)")

    # --- Relatório de atualizações do dicionário ---
    print("\n📘 Relatório de atualizações do dicionário:")
    overwritten = []  # sobrescritas
    preserved = []    # antigas preservadas
    new_entries = []  # novas adições

    for k in sorted(update_map_local.keys()):
        old_val = update_map.get(k)
        new_val = update_map_local[k]
        if old_val and old_val != new_val:
            overwritten.append((k, old_val, new_val))
        elif not old_val:
            new_entries.append((k, new_val))
        else:
            preserved.append((k, new_val))

    if overwritten:
        print("  ✏️ Sobrescritas:")
        for k, old, new in overwritten:
            print(f"     {k}: {old} → {new}")
    else:
        print("  ✏️ Sobrescritas:\n     (nenhuma)")

    if new_entries:
        print("  ➕ Novas entradas adicionadas:")
        for k, v in new_entries:
            print(f"     {k} → {v}")
    else:
        print("  ➕ Novas entradas adicionadas:\n     (nenhuma)")

    if preserved:
        print("  🗂️ Entradas antigas preservadas (sem modificação):")
        for k, v in preserved:
            print(f"     {k} → {v}")
    else:
        print("  🗂️ Nenhuma entrada preservada.")

if __name__ == "__main__":
    main()
