"""Reproduce the real version-lens example locally; this makes no AI/network calls."""

import platform
import queue


def main():
    print(f"Observed runtime: {platform.python_implementation()} {platform.python_version()}")
    if not hasattr(queue.Queue, "shutdown"):
        print("Queue.shutdown is absent on this runtime. Use Python 3.13+ to run the shutdown example.")
        return
    immediate = queue.Queue()
    immediate.put("unprocessed job")
    immediate.shutdown(immediate=True)
    immediate.join()
    assert immediate.unfinished_tasks == 0
    try:
        immediate.get_nowait()
    except queue.ShutDown:
        pass
    else:
        raise AssertionError("Immediate shutdown should have drained the queued item")
    print("Immediate shutdown: join returned, but the queued job was never processed.")

    draining = queue.Queue()
    draining.put("job to finish")
    draining.shutdown(immediate=False)
    completed = draining.get_nowait()
    draining.task_done()
    draining.join()
    assert completed == "job to finish" and draining.unfinished_tasks == 0
    print("Normal draining: retrieved the job, marked it done, then join returned.")
    print("PASS: join completion behavior depends on the shutdown mode.")


if __name__ == "__main__":
    main()
