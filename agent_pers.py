from __future__ import annotations
"""
Обертка для обратной совместимости.
Основной код перенесен в пакет `agents/`.
Публичный API: analyze, analyze_async и модели/утилиты через `agents`.

Использование:
  python agent_pers.py <путь_к_json_файлу>
  python agent_pers.py < snapshot.json
  echo '{"schema_version": "1.0", ...}' | python agent_pers.py
"""
import json
import sys
from agents import analyze, analyze_async, analyze_from_file


def main():
    """Обрабатывает данные из файла или stdin"""
    # Вариант 1: Файл передан как аргумент
    if len(sys.argv) >= 2:
        file_path = sys.argv[1]
        res = analyze_from_file(file_path)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    
    # Вариант 2: Данные из stdin (для внешних источников)
    if not sys.stdin.isatty():  # Проверяем, что есть данные в stdin
        try:
            data = json.load(sys.stdin)
            if isinstance(data, list):
                # Массив снапшотов
                from agents import analyze_batch
                res = analyze_batch(data)
            elif isinstance(data, dict) and "snapshots" in data:
                # Объект с ключом snapshots
                from agents import analyze_batch
                res = analyze_batch(data["snapshots"])
            else:
                # Один снапшот
                res = analyze(data)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return
        except json.JSONDecodeError as e2:
            print(f"Ошибка парсинга JSON из stdin: {e2}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка обработки данных: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Если ничего не передано - показываем справку
    print("Использование:", file=sys.stderr)
    print("  python agent_pers.py <путь_к_json_файлу>", file=sys.stderr)
    print("  python agent_pers.py < snapshot.json", file=sys.stderr)
    print("  echo '{\"schema_version\": \"1.0\", ...}' | python agent_pers.py", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
