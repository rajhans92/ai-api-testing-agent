import asyncio
import time

TPM_LIMIT = 30000
SAFETY_BUFFER = 5000

current_tokens = 0
window_start = time.time()

async def wait_for_token_limit(estimated_tokens):

    global current_tokens, window_start

    now = time.time()

    # reset every minute
    if now - window_start >= 60:
        current_tokens = 0
        window_start = now

    # wait if limit exceeded
    if ((current_tokens + estimated_tokens) > (TPM_LIMIT-SAFETY_BUFFER)):

        wait_time = 60 - (now - window_start)

        print("---------------------------------------------------------------------------------------------")
        print("---------------------------------------------------------------------------------------------")
        print(f"Sleeping for {wait_time:.2f}s")
        print("---------------------------------------------------------------------------------------------")
        print("---------------------------------------------------------------------------------------------")
        
        await asyncio.sleep(wait_time)

        current_tokens = 0
        window_start = time.time()

    current_tokens += estimated_tokens