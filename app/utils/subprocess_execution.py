import asyncio


async def run_command(command: list[str], expected_error: str | None = None) -> tuple[str, int]:
    """
    Run a subprocess and return the output
    """
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        if expected_error and expected_error in stderr.decode():
            return stdout.decode(), proc.returncode
        raise RuntimeError(f"Command failed with return code {proc.returncode}: {stderr.decode()}")

    return stdout.decode(), proc.returncode
