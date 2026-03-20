#!/usr/bin/env python3
"""
Pytest fixtures for home-miner-daemon tests.
"""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

import pytest


@pytest.fixture(scope="session")
def state_dir(tmp_path_factory):
    """Create a temporary state directory for tests."""
    return tmp_path_factory.mktemp("state")


@pytest.fixture(scope="session")
def daemon_port(tmp_path_factory):
    """Allocate a port for the daemon."""
    return 18080  # Fixed port for test session


@pytest.fixture(scope="module")
def daemon_url(daemon_port, daemon_process):
    """
    Base URL for daemon HTTP endpoints.
    Depends on daemon_process to ensure daemon is started.
    """
    return f"http://127.0.0.1:{daemon_port}"


@pytest.fixture(scope="module")
def daemon_process(state_dir, daemon_port):
    """
    Start the daemon with isolated state for the test module.
    Automatically cleans up on teardown.
    """
    # Set up environment
    env = os.environ.copy()
    env["ZEND_STATE_DIR"] = str(state_dir)
    env["ZEND_BIND_HOST"] = "127.0.0.1"
    env["ZEND_BIND_PORT"] = str(daemon_port)

    # Find daemon.py
    daemon_py = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "daemon.py"
    )

    # Start daemon
    proc = subprocess.Popen(
        [sys.executable, daemon_py],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for daemon to be ready
    url = f"http://127.0.0.1:{daemon_port}/health"
    for _ in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError("Daemon failed to start")

    yield proc

    # Teardown: stop daemon
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture
def daemon_url_with_process(daemon_url, daemon_process):
    """Provide daemon_url with assurance that daemon_process is running."""
    return daemon_url
