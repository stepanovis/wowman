"""
Unit tests for cycle calculator module.

Тесты для модуля расчета менструального цикла, овуляции,
фертильного окна и безопасных периодов.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

import pytest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from utils.cycle_calculator import (
    calculate_ovulation,
    calculate_fertile_window,
    calculate_safe_periods,
    calculate_next_period,
    calculate_current_phase,
    format_date_for_user,
    convert_date_to_user_timezone,
    convert_date_from_user_timezone,
    get_notification_datetime
)


class TestOvulationCalculation:
    """Тесты для расчета даты овуляции."""

    def test_normal_cycle(self):
        """Тест расчета овуляции для обычного цикла (28 дней)."""
        start_date = date(2025, 9, 1)
        cycle_length = 28

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция должна быть на 15-й день (cycle_length - 14 = 14, начиная с 1 сентября это 15 сентября)
        expected_date = date(2025, 9, 15)
        assert ovulation_date == expected_date

    def test_short_cycle(self):
        """Тест расчета овуляции для короткого цикла (21 день)."""
        start_date = date(2025, 9, 1)
        cycle_length = 21

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция: start_date + (21 - 14) = 1 сент + 7 дней = 8 сентября
        expected_date = date(2025, 9, 8)
        assert ovulation_date == expected_date

    def test_long_cycle(self):
        """Тест расчета овуляции для длинного цикла (35 дней)."""
        start_date = date(2025, 9, 1)
        cycle_length = 35

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция: start_date + (35 - 14) = 1 сент + 21 день = 22 сентября
        expected_date = date(2025, 9, 22)
        assert ovulation_date == expected_date

    def test_boundary_cycle_40_days(self):
        """Тест расчета овуляции для максимально длинного цикла (40 дней)."""
        start_date = date(2025, 1, 1)
        cycle_length = 40

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция: start_date + (40 - 14) = 1 янв + 26 дней = 27 января
        expected_date = date(2025, 1, 27)
        assert ovulation_date == expected_date

    def test_month_transition(self):
        """Тест расчета овуляции с переходом на следующий месяц."""
        start_date = date(2025, 9, 20)
        cycle_length = 28

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция: 20 сент + (28 - 14) = 20 сент + 14 = 4 октября
        expected_date = date(2025, 10, 4)
        assert ovulation_date == expected_date

    def test_year_transition(self):
        """Тест расчета овуляции с переходом на следующий год."""
        start_date = date(2024, 12, 20)
        cycle_length = 28

        ovulation_date = calculate_ovulation(start_date, cycle_length)

        # Овуляция: 20 дек + (28 - 14) = 20 дек + 14 = 3 января
        expected_date = date(2025, 1, 3)
        assert ovulation_date == expected_date


class TestFertileWindow:
    """Тесты для расчета фертильного окна."""

    def test_normal_fertile_window(self):
        """Тест расчета фертильного окна для обычного цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28

        ovulation_date = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

        # Фертильное окно: 5 дней до овуляции и 1 день после
        # Овуляция 15 сентября, окно с 10 по 16 сентября
        assert fertile_start == date(2025, 9, 10)
        assert fertile_end == date(2025, 9, 16)

    def test_short_cycle_fertile_window(self):
        """Тест фертильного окна для короткого цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 21

        ovulation_date = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

        # Овуляция 8 сентября, окно с 3 по 9 сентября
        assert fertile_start == date(2025, 9, 3)
        assert fertile_end == date(2025, 9, 9)

    def test_fertile_window_duration(self):
        """Проверка, что фертильное окно всегда длится 7 дней."""
        for cycle_length in [21, 25, 28, 32, 35, 40]:
            start_date = date(2025, 9, 1)
            ovulation_date = calculate_ovulation(start_date, cycle_length)
            fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

            # Фертильное окно должно быть 7 дней (включительно)
            duration = (fertile_end - fertile_start).days + 1
            assert duration == 7, f"Неверная длительность окна для цикла {cycle_length} дней"

    def test_month_boundary_fertile_window(self):
        """Тест фертильного окна при переходе через границу месяца."""
        start_date = date(2025, 8, 25)
        cycle_length = 28

        ovulation_date = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation_date)

        # Овуляция 8 сентября (25 авг + 14 дней), окно с 3 по 9 сентября
        assert fertile_start == date(2025, 9, 3)
        assert fertile_end == date(2025, 9, 9)


class TestSafePeriods:
    """Тесты для расчета безопасных периодов."""

    def test_normal_safe_periods(self):
        """Тест расчета безопасных периодов для обычного цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        safe_before, safe_after = calculate_safe_periods(
            start_date, cycle_length, period_length
        )

        # Безопасный период до: после месячных (6 сентября) до начала фертильного окна
        # С учетом запаса в 2 дня, первый безопасный период может быть очень коротким или отсутствовать
        # Проверяем логику безопасных периодов
        if safe_before:
            assert safe_before[0] >= start_date + timedelta(days=period_length)
            assert safe_before[1] < date(2025, 9, 10) - timedelta(days=2)  # До фертильного окна (10 сент) с запасом

        # Безопасный период после фертильного окна
        if safe_after:
            assert safe_after[0] > date(2025, 9, 16) + timedelta(days=2)  # После фертильного окна (16 сент) с запасом
            assert safe_after[1] <= date(2025, 9, 28)  # До следующих месячных

    def test_long_cycle_safe_periods(self):
        """Тест безопасных периодов для длинного цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 35
        period_length = 5

        safe_before, safe_after = calculate_safe_periods(
            start_date, cycle_length, period_length
        )

        # При длинном цикле больше безопасных дней
        ovulation = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation)

        # Должны быть оба безопасных периода
        assert safe_before is not None
        assert safe_after is not None

        # Проверяем, что безопасные периоды не пересекаются с фертильным окном
        if safe_before:
            assert safe_before[1] < fertile_start - timedelta(days=2)
        if safe_after:
            assert safe_after[0] > fertile_end + timedelta(days=2)

    def test_short_cycle_minimal_safe_periods(self):
        """Тест минимальных безопасных периодов для короткого цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 21
        period_length = 5

        safe_before, safe_after = calculate_safe_periods(
            start_date, cycle_length, period_length
        )

        # При коротком цикле очень мало безопасных дней
        # Первый безопасный период скорее всего отсутствует
        # Второй безопасный период должен быть короткий
        if safe_after:
            duration = (safe_after[1] - safe_after[0]).days + 1
            assert duration > 0  # Должен быть хотя бы один день


class TestNextPeriod:
    """Тесты для расчета даты следующих месячных."""

    def test_normal_next_period(self):
        """Тест расчета следующих месячных для обычного цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28

        next_period = calculate_next_period(start_date, cycle_length)

        assert next_period == date(2025, 9, 29)

    def test_february_next_period(self):
        """Тест расчета с учетом февраля (короткий месяц)."""
        start_date = date(2025, 2, 1)
        cycle_length = 30

        next_period = calculate_next_period(start_date, cycle_length)

        assert next_period == date(2025, 3, 3)

    def test_leap_year_february(self):
        """Тест расчета в високосном году."""
        start_date = date(2024, 2, 1)
        cycle_length = 30

        next_period = calculate_next_period(start_date, cycle_length)

        # 2024 - високосный год, февраль имеет 29 дней
        assert next_period == date(2024, 3, 2)

    def test_year_transition_next_period(self):
        """Тест перехода на следующий год."""
        start_date = date(2024, 12, 15)
        cycle_length = 28

        next_period = calculate_next_period(start_date, cycle_length)

        assert next_period == date(2025, 1, 12)


class TestCurrentPhase:
    """Тесты для определения текущей фазы цикла."""

    def test_menstruation_phase(self):
        """Тест фазы менструации."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 9, 3)  # 3-й день цикла

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["phase"] == "menstruation"
        assert phase_info["day"] == 3
        assert phase_info["description"] == "Менструация"

    def test_follicular_phase(self):
        """Тест фолликулярной фазы."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 9, 8)  # 8-й день цикла

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["phase"] == "follicular"
        assert phase_info["day"] == 8

    def test_ovulation_phase(self):
        """Тест фазы овуляции."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 9, 14)  # День овуляции

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["phase"] == "ovulation"
        assert phase_info["description"] == "Овуляция"

    def test_luteal_phase(self):
        """Тест лютеиновой фазы."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 9, 20)  # 20-й день цикла

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["phase"] == "luteal"
        assert phase_info["description"] == "Лютеиновая фаза"

    def test_pre_menstruation_phase(self):
        """Тест предменструальной фазы (ПМС)."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 9, 27)  # За 2 дня до месячных

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["phase"] == "pre_menstruation"
        assert phase_info["description"] == "Предменструальный период"

    def test_fertile_period_check(self):
        """Тест проверки фертильного периода."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        # Тестируем день в фертильном окне
        current_date = date(2025, 9, 10)  # В фертильном окне
        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["is_fertile"] == True

        # Тестируем день вне фертильного окна
        current_date = date(2025, 9, 20)  # Вне фертильного окна
        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        assert phase_info["is_fertile"] == False

    def test_phase_after_multiple_cycles(self):
        """Тест определения фазы после нескольких циклов."""
        start_date = date(2025, 1, 1)
        cycle_length = 28
        period_length = 5
        current_date = date(2025, 3, 15)  # Через несколько циклов

        phase_info = calculate_current_phase(
            start_date, cycle_length, period_length, current_date
        )

        # Должен корректно рассчитать фазу с учетом прошедших циклов
        assert phase_info["day"] > 0 and phase_info["day"] <= cycle_length
        assert phase_info["phase"] in ["menstruation", "follicular", "ovulation", "luteal", "pre_menstruation"]


class TestDateFormatting:
    """Тесты для форматирования дат."""

    def test_format_date_with_weekday(self):
        """Тест форматирования даты с днем недели."""
        test_date = date(2025, 9, 15)  # Понедельник
        formatted = format_date_for_user(test_date)

        # Функция должна включать день недели по умолчанию
        assert "15" in formatted
        assert "сентябр" in formatted.lower()

    def test_format_date_without_weekday(self):
        """Тест форматирования даты без дня недели."""
        test_date = date(2025, 9, 15)
        formatted = format_date_for_user(test_date, include_weekday=False)

        # Должна содержать дату без дня недели
        assert "15" in formatted
        assert "сентябр" in formatted.lower()


class TestTimezoneConversions:
    """Тесты для работы с часовыми поясами."""

    def test_convert_to_user_timezone(self):
        """Тест конвертации в часовой пояс пользователя."""
        # Создаем datetime в UTC
        utc_dt = datetime(2025, 9, 15, 12, 0, tzinfo=ZoneInfo("UTC"))

        # Конвертируем в московское время
        moscow_dt = convert_date_to_user_timezone(utc_dt, "Europe/Moscow")

        # Московское время на 3 часа впереди UTC
        assert moscow_dt.hour == 15  # 12 + 3 = 15

    def test_convert_from_user_timezone(self):
        """Тест конвертации из часового пояса пользователя в UTC."""
        # Создаем datetime в московском времени
        moscow_dt = datetime(2025, 9, 15, 15, 0, tzinfo=ZoneInfo("Europe/Moscow"))

        # Конвертируем в UTC
        utc_dt = convert_date_from_user_timezone(moscow_dt, "Europe/Moscow")

        # UTC на 3 часа позади московского времени
        assert utc_dt.hour == 12  # 15 - 3 = 12

    def test_notification_datetime_morning(self):
        """Тест создания времени уведомления утром."""
        notification_date = date(2025, 9, 15)
        user_timezone = "Europe/Moscow"

        notification_dt = get_notification_datetime(
            notification_date,
            notification_time="09:00",
            user_timezone=user_timezone
        )

        # Функция возвращает UTC время, проверяем конвертацию
        # Московское время 09:00 = UTC 06:00 (UTC+3)
        assert notification_dt.date() == notification_date
        assert notification_dt.hour == 6  # 09:00 Moscow = 06:00 UTC
        assert notification_dt.minute == 0
        assert notification_dt.tzinfo == ZoneInfo("UTC")

    def test_notification_datetime_with_days_before(self):
        """Тест создания времени уведомления за несколько дней до события."""
        target_date = date(2025, 9, 15)
        user_timezone = "Europe/Moscow"

        notification_dt = get_notification_datetime(
            target_date,
            notification_time="20:00",
            user_timezone=user_timezone,
            days_before=2
        )

        # Уведомление должно быть за 2 дня до целевой даты
        # Московское время 20:00 = UTC 17:00 (UTC+3)
        assert notification_dt.date() == date(2025, 9, 13)
        assert notification_dt.hour == 17  # 20:00 Moscow = 17:00 UTC
        assert notification_dt.tzinfo == ZoneInfo("UTC")


class TestEdgeCases:
    """Тесты граничных случаев."""

    def test_very_irregular_cycle(self):
        """Тест для очень нерегулярного цикла."""
        start_date = date(2025, 9, 1)

        # Минимальный цикл
        min_cycle = 21
        ovulation = calculate_ovulation(start_date, min_cycle)
        assert ovulation == date(2025, 9, 8)  # 1 сент + 7 дней = 8 сент

        # Максимальный цикл
        max_cycle = 40
        ovulation = calculate_ovulation(start_date, max_cycle)
        assert ovulation == date(2025, 9, 27)  # 1 сент + 26 дней = 27 сент

        # Разница в днях овуляции
        difference = (date(2025, 9, 27) - date(2025, 9, 8)).days
        assert difference == 19  # Большая разница для нерегулярных циклов

    def test_cycle_calculation_consistency(self):
        """Тест консистентности расчетов цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        # Рассчитываем все ключевые даты
        ovulation = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation)
        next_period = calculate_next_period(start_date, cycle_length)

        # Проверяем консистентность
        # Овуляция должна быть в середине фертильного окна (примерно)
        assert fertile_start < ovulation <= fertile_end

        # Следующие месячные через cycle_length дней
        assert (next_period - start_date).days == cycle_length

        # Овуляция за 14 дней до следующих месячных
        assert (next_period - ovulation).days == 14

    def test_safe_periods_overlap_check(self):
        """Проверка, что безопасные периоды не пересекаются с фертильным окном."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        ovulation = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation)
        safe_before, safe_after = calculate_safe_periods(
            start_date, cycle_length, period_length
        )

        if safe_before:
            # Безопасный период до должен заканчиваться до фертильного окна
            assert safe_before[1] < fertile_start - timedelta(days=2)

        if safe_after:
            # Безопасный период после должен начинаться после фертильного окна
            assert safe_after[0] > fertile_end + timedelta(days=2)


class TestIntegration:
    """Интеграционные тесты для проверки совместной работы функций."""

    def test_full_cycle_calculation(self):
        """Полный тест расчета всех параметров цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        # Рассчитываем все параметры
        ovulation = calculate_ovulation(start_date, cycle_length)
        fertile_start, fertile_end = calculate_fertile_window(ovulation)
        safe_before, safe_after = calculate_safe_periods(start_date, cycle_length, period_length)
        next_period = calculate_next_period(start_date, cycle_length)

        # Проверяем логическую последовательность дат
        dates_in_order = [start_date]

        if safe_before:
            dates_in_order.extend([safe_before[0], safe_before[1]])

        dates_in_order.extend([fertile_start, ovulation, fertile_end])

        if safe_after:
            dates_in_order.extend([safe_after[0], safe_after[1]])

        dates_in_order.append(next_period)

        # Все даты должны идти в хронологическом порядке
        for i in range(len(dates_in_order) - 1):
            assert dates_in_order[i] <= dates_in_order[i + 1], \
                f"Нарушен порядок дат: {dates_in_order[i]} > {dates_in_order[i + 1]}"

    def test_phase_transitions(self):
        """Тест переходов между фазами цикла."""
        start_date = date(2025, 9, 1)
        cycle_length = 28
        period_length = 5

        phases_seen = set()

        # Проходим по всему циклу день за днем
        for day_offset in range(cycle_length):
            current_date = start_date + timedelta(days=day_offset)
            phase_info = calculate_current_phase(
                start_date, cycle_length, period_length, current_date
            )
            phases_seen.add(phase_info["phase"])

        # Должны увидеть основные фазы
        expected_phases = {"menstruation", "follicular", "ovulation", "luteal"}

        # Проверяем, что хотя бы основные фазы присутствуют
        assert expected_phases.issubset(phases_seen), \
            f"Не все фазы обнаружены. Найдены: {phases_seen}"


if __name__ == "__main__":
    # Запуск тестов при прямом выполнении файла
    pytest.main([__file__, "-v"])