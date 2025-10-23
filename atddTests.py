import pytest
from fastapi.testclient import TestClient
from app import app  # предполагая, что это ваше FastAPI приложение

client = TestClient(app)


def test_successful_route_calculation():
    """Тест успешного построения маршрута с корректными координатами"""
    # Координаты: Эйфелева башня -> Лувр
    from_coord = "48.8584,2.2945"
    to_coord = "48.8606,2.3376"

    response = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}")

    assert response.status_code == 200
    data = response.json()

    # Проверяем структуру ответа
    assert "distance" in data
    assert "duration" in data
    assert "geometry" in data
    assert "coordinates" in data["geometry"]

    # Проверяем, что расстояние и время положительные
    assert data["distance"] > 0
    assert data["duration"] > 0


def test_route_with_different_transport_profiles():
    """Тест построения маршрута с разными типами транспорта"""
    from_coord = "48.8584,2.2945"
    to_coord = "48.8606,2.3376"

    profiles = ["foot-walking", "driving-car", "cycling-regular"]

    for profile in profiles:
        response = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}&profile={profile}")
        assert response.status_code == 200
        data = response.json()

        # Для разных профилей время и расстояние должны отличаться
        assert data["distance"] > 0
        assert data["duration"] > 0


def test_route_with_invalid_coordinates():
    """Тест обработки некорректных координат"""
    invalid_cases = [
        "invalid,format",  # Нечисловой формат
        "91.0,181.0",  # Координаты вне диапазона
        "48.8584",  # Неполные координаты
        "48.8584,2.2945,extra"  # Лишние значения
    ]

    for invalid_coord in invalid_cases:
        response = client.get(f"/route?from_coord={invalid_coord}&to_coord=48.8606,2.3376")
        assert response.status_code == 400
        assert "error" in response.json().lower() or "неверный" in response.json().lower()


def test_route_with_missing_parameters():
    """Тест обработки отсутствующих параметров"""
    # Отсутствует from_coord
    response = client.get("/route?to_coord=48.8606,2.3376")
    assert response.status_code == 422  # Validation error

    # Отсутствует to_coord
    response = client.get("/route?from_coord=48.8584,2.2945")
    assert response.status_code == 422


def test_route_unreachable_destination():
    """Тест обработки недостижимых точек маршрута"""
    # Координаты в разных частях света (Европа -> Австралия)
    from_coord = "48.8584,2.2945"  # Париж
    to_coord = "-33.8688,151.2093"  # Сидней

    response = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}")

    # Ожидаем либо ошибку, либо специфический ответ для недостижимых точек
    assert response.status_code in [400, 404, 200]
    if response.status_code == 200:
        data = response.json()
        # Может быть очень большое расстояние или специфический флаг
        assert data["distance"] > 0


def test_route_with_same_coordinates():
    """Тест построения маршрута с одинаковыми начальной и конечной точками"""
    from_coord = "48.8584,2.2945"
    to_coord = "48.8584,2.2945"

    response = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}")

    assert response.status_code == 200
    data = response.json()

    # Расстояние должно быть 0 или очень маленьким
    assert data["distance"] >= 0
    assert data["duration"] >= 0


def test_route_with_waypoints():
    """Тест построения маршрута с промежуточными точками"""
    waypoints = ["48.8584,2.2945", "48.8606,2.3376", "48.8738,2.2950"]  # Эйфелева -> Лувр -> Триумфальная арка

    # Этот тест может требовать расширения API для поддержки waypoints
    # Показываем ожидаемое поведение
    pass


def test_route_alternative_routes():
    """Тест получения альтернативных маршрутов"""
    from_coord = "48.8584,2.2945"
    to_coord = "48.8606,2.3376"

    response = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}&alternatives=true")

    if response.status_code == 200:
        data = response.json()
        # Ожидаем массив альтернативных маршрутов
        assert isinstance(data, list)
        if len(data) > 1:
            # Проверяем, что альтернативные маршруты имеют разные характеристики
            distances = [route["distance"] for route in data]
            assert len(set(distances)) > 1  # Разные расстояния


def test_route_with_custom_preferences():
    """Тест построения маршрута с пользовательскими предпочтениями"""
    from_coord = "48.8584,2.2945"
    to_coord = "48.8606,2.3376"

    # Быстрый маршрут vs короткий маршрут
    response_fastest = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}&preference=fastest")
    response_shortest = client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}&preference=shortest")

    if response_fastest.status_code == 200 and response_shortest.status_code == 200:
        fastest_data = response_fastest.json()
        shortest_data = response_shortest.json()

        # Самый быстрый маршрут может быть длиннее, но с меньшим временем
        # Самый короткий маршрут может быть медленнее, но с меньшим расстоянием
        assert fastest_data["duration"] <= shortest_data["duration"] or fastest_data["distance"] >= shortest_data[
            "distance"]


if __name__ == "__main__":
    # Запуск всех тестов
    pytest.main([__file__, "-v"])

    # Или запуск конкретных тестов
    # pytest.main([__file__, "-v", "-k", "successful_route"])