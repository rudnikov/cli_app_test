import pytest
from main import DjangoLogAnalyzer


@pytest.fixture
def sample_logs(tmp_path):
    log_content = """2025-03-27 12:36:45,000 INFO django.request: GET /api/v1/checkout/\n
    2025-03-27 12:29:35,000 INFO django.request: GET /api/v1/orders/\n
    2025-03-27 12:33:05,000 ERROR django.request: POST /api/v1/users/\n
    2025-03-27 12:35:19,000 WARNING django.security: SuspiciousOperation\n
    2025-03-27 12:10:49,000 CRITICAL django.core.management: OSError"""
    log_file = tmp_path / "test.log"
    log_file.write_text(log_content)
    return str(log_file)


def test_handler_and_level_sorting(sample_logs, capsys):
    """Тестирование сортировки хэндлеров и уровней логирования"""
    analyzer = DjangoLogAnalyzer([sample_logs], "handlers")
    analyzer.generate_report()

    captured = capsys.readouterr()
    output = captured.out.splitlines()

    # Проверяем сортировку хэндлеров
    handlers = [line.split()[0] for line in output if line.startswith('/')]
    assert handlers == sorted(handlers)

    # Проверяем сортировку уровней логирования
    header = next(line for line in output if line.startswith('HANDLER'))
    levels = header.split()[1:]
    assert levels == sorted(levels)


def test_url_extraction():
    """Проверка корректности извлечения URL из сообщений"""
    test_messages = [
        "GET /api/v1/test/",
        "POST /admin/login/",
        "Internal Server Error: /api/v1/users/"
    ]

    for msg in test_messages:
        match = DjangoLogAnalyzer.HANDLER_PATTERN.search(msg)
        assert match is not None
        assert match.group().startswith('/')


def test_multiple_files_processing(tmp_path):
    """Тестирование обработки нескольких файлов"""
    # Создаем два тестовых файла
    file1 = tmp_path / "file1.log"
    file1.write_text("2025-03-27 12:00:00,000 INFO django.request: GET /api/v1/file1/")

    file2 = tmp_path / "file2.log"
    file2.write_text("2025-03-27 12:00:01,000 ERROR django.request: POST /api/v1/file2/")

    analyzer = DjangoLogAnalyzer([str(file1), str(file2)], "handlers")
    assert len(analyzer.logs) == 2
    assert {log['message'] for log in analyzer.logs} == {
        "GET /api/v1/file1/",
        "POST /api/v1/file2/"
    }


def test_logger_filtering(sample_logs):
    """Проверка фильтрации по логгеру (только django.request)"""
    analyzer = DjangoLogAnalyzer([sample_logs], "handlers")
    assert len(analyzer.logs) == 3  # Только 3 записи django.request из 5
    assert all(log['logger'] == 'django.request' for log in analyzer.logs)


def test_table_headers(sample_logs, capsys):
    """Тестирование заголовков таблицы"""
    analyzer = DjangoLogAnalyzer([sample_logs], "handlers")
    analyzer.generate_report()

    captured = capsys.readouterr()
    header = next(line for line in captured.out.split('\n') if line.startswith('HANDLER'))

    assert "HANDLER" in header
    assert "INFO" in header
    assert "ERROR" in header
    assert "WARNING" not in header  # Не должно быть в заголовке, так как нет WARNING для django.request


def test_total_requests_count(sample_logs, capsys):
    """Проверка подсчета общего количества запросов"""
    analyzer = DjangoLogAnalyzer([sample_logs], "handlers")
    print(analyzer.generate_report())

    captured = capsys.readouterr()
    print(captured)
    total_line = [line for line in captured.out.split('\n') if "Total requests:" in line][0]

    assert "Total requests: 3" in total_line  # 3 корректных записи django.request


def test_column_formatting(sample_logs, capsys):
    """Проверка форматирования столбцов"""
    analyzer = DjangoLogAnalyzer([sample_logs], "handlers")
    analyzer.generate_report()

    captured = capsys.readouterr()
    lines = [line for line in captured.out.split('\n') if line.startswith('/')]

    for line in lines:
        parts = line.split()
        # Проверяем что хэндлер занимает 30 символов
        assert len(parts[0]) <= 30
        # Проверяем выравнивание чисел
        assert all(len(part) <= 10 for part in parts[1:])
