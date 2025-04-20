import argparse
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class DjangoLogAnalyzer:
    """Анализатор логов Django"""

    # Регулярные выражения для парсинга логов
    LOG_PATTERN = re.compile(
        r'^(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3} '
        r'(?P<level>\w+) '
        r'(?P<logger>[\w\.]+): '
        r'(?P<message>.+)$'
    )

    HANDLER_PATTERN = re.compile(
        r'(/[^\s]+)'
    )

    # Словарь для хранения регулярных выражений по поиску подстрок в логах для формирования отчетов
    REPORT_DICT = {
        'handlers': ['django.request']
    }

    NAME_LOGS = set()  # Множество с типами логов

    def __init__(self, log_files: list[str], report_name: str):
        self.log_files = [str(Path(path)) for path in log_files]
        self.logs = list()  # Список для хранения логов
        self.report_name = report_name  # str переменная для хранения типа отчета
        self._parse_logs()

    def _parse_logs(self):
        """Парсинг всех лог-файлов"""
        for file_path in self.log_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        return_match = self.LOG_PATTERN.match(line)
                        if return_match['logger'] in self.REPORT_DICT[self.report_name]:
                            log_entry = return_match.groupdict()
                            log_entry['date'] = datetime.strptime(
                                log_entry['date'], '%Y-%m-%d %H:%M:%S'
                            )
                            self.logs.append(log_entry)
                            self.NAME_LOGS.add(log_entry['level'])
            except FileNotFoundError:
                print(f"\033[41m\033[32mWarning: File {file_path} not found\033[0m")
            except Exception as e:
                print(f"\033[41m\033[32mError reading file {file_path}: {str(e)}\033[0m")

    def _report_handlers(self):
        """Отчёт о состоянии ручек API по каждому уровню логирования"""
        sort_name_logs = sorted(self.NAME_LOGS)
        handler_errors = defaultdict(lambda: defaultdict(int))
        for log in self.logs:
            match = self.HANDLER_PATTERN.search(log['message'])
            if not match:
                continue

            handlers = match.group()
            handler_errors[handlers][log['level']] += 1

        # Добавляем нулевые уровни для каждого handler
        for handler in handler_errors:
            for level in sort_name_logs:
                if level not in handler_errors[handler]:
                    handler_errors[handler][level] = 0

        # Выводим отчет
        # Строка заголовка отчета
        print(f"{'HANDLER':<30}" + "".join([f"{elem:<10}" for elem in sort_name_logs]))
        # Тело отчета
        for handler, logs in sorted(handler_errors.items()):
            print(
                f"{handler:<30}" + "".join([f"{logs[elem]:<10}" for elem in sort_name_logs])
            )
        # Количество запросов в отчете
        print(f"\nTotal requests: {sum(sum(elem.values()) for elem in handler_errors.values())}\n")

    def generate_report(self) -> str:
        """Генерация отчета по имени"""
        report_method = getattr(self, f'_report_{self.report_name}', None)
        if report_method is None:
            return f"Unknown report: {self.report_name}"
        return report_method()


def main():
    parser = argparse.ArgumentParser(
        description='Django Log Analyzer'
    )
    parser.add_argument(
        'log_files',
        metavar='LOG_FILE',
        type=str,
        nargs='+',
        help='Path to log file(s)'
    )
    parser.add_argument(
        '--report',
        type=str,
        required=True,
        choices=['handlers'],  # Тут можно добавить возможность для определения новых отчетов
        help='Report type to generate:\n'
             '\thandlers - errors by handlers\n'
    )
    # Проверка названия отчета
    try:
        args = parser.parse_args()
    except SystemExit:
        # Ошибка выбора отчета
        print(f"\033[41m\033[32mError: There is no such report form.\033[0m")

    # Проверка существования файлов
    valid_files = []
    try:
        for file_path in args.log_files:
            if Path(file_path).exists():
                valid_files.append(file_path)
            else:
                # Вызов исключения из-за отсутствия файла с нужным названием
                raise Exception(f"\033[41m\033[32mWarning: File {file_path} does not exist and will be skipped\033[0m")
        # Составление отчета если все файлы найдены
        try:
            analyzer = DjangoLogAnalyzer(valid_files, args.report)
            analyzer.generate_report()
        except Exception as err:
            print(f"\033[41m\033[32mError generating report: {str(err)}\033[0m")
    except Exception as err:
        # Ошибка чтения файла.
        print(err.args[0])


if __name__ == '__main__':
    main()
