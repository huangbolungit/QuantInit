import pytest

from app.services.data_sources.manager import DataSourceManager


@pytest.mark.asyncio
async def test_market_overview_available():
    manager = DataSourceManager()
    overview = await manager.get_market_overview()
    await manager.close()
    assert isinstance(overview, dict)
    assert overview


@pytest.mark.asyncio
async def test_sector_and_heatmap_data():
    manager = DataSourceManager()
    sectors = await manager.get_sector_performance(limit=5)
    heatmap = await manager.get_market_heatmap()
    await manager.close()

    assert isinstance(sectors, list)
    assert isinstance(heatmap, list)
    assert heatmap == [] or isinstance(heatmap[0], dict)


@pytest.mark.asyncio
async def test_index_data_fallback():
    manager = DataSourceManager()
    data = await manager.get_index_data("000001")
    await manager.close()

    assert isinstance(data, dict)
    assert data.get("code") == "000001"
