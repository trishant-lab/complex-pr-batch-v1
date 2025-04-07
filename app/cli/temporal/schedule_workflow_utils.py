from app.cli.temporal.core.connection import get_temporal_client


async def remove_schedule(schedule_id: str) -> None:
    """
    Remove the schedule with the given id
    """
    client = await get_temporal_client()
    handle = client.get_schedule_handle(id=schedule_id)
    await handle.delete()


async def remove_redundant_schedules() -> None:
    """
    Remove the schedules which arein
    """
    from app.core.cli_settings import get_schedules

    schedules = get_schedules()
    client = await get_temporal_client()

    async for schedule in await client.list_schedules():
        if schedule.id not in schedules:
            await remove_schedule(schedule.id)
