import logging
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import timezone
from pathlib import Path
from typing import Any, Generator

import dill
import pandas as pd
from pyarrow import ArrowInvalid

from nanoeval._persistent_db import database_dir

logger = logging.getLogger(__name__)


def _fetch_table_data(table_name: str, _conn: sqlite3.Connection) -> pd.DataFrame:
    cur = _conn.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()
    columns = [description[0] for description in cur.description]
    df = pd.DataFrame(rows, columns=columns)

    return df


@contextmanager
def _monitor_conn(file: Path) -> Generator[sqlite3.Connection, None, None]:
    with closing(sqlite3.connect(file)) as conn:
        yield conn


def _load_result(data: bytes | None) -> Any:
    from nanoeval._executor_worker import ExecutorExceptionWrapper

    if data is None:
        return None

    try:
        deserialized = dill.loads(data)
    except ArrowInvalid:
        logger.warning("Failed to deserialize result, returning None", exc_info=True)
        return None
    if isinstance(deserialized, ExecutorExceptionWrapper):
        return deserialized.traceback

    return deserialized


_STATUSES: dict[str, str] = {
    "initialized": "result IS NULL AND executor_pid IS NULL",
    "running": "result IS NULL AND executor_pid IS NOT NULL",
    "errored": "result LIKE '%RetryableSystemError%'",
    "completed": "result NOT NULL",
}


def _load_task_data(
    conn: sqlite3.Connection, eval_data: pd.DataFrame, eval_name_filter: str, status_filter: str
) -> pd.DataFrame:
    """
    Creates and processes task data based on the provided filters.

    Args:
        conn (sqlite3.Connection): SQLite connection object.
        eval_data (pd.DataFrame): DataFrame containing evaluation data.
        eval_name_filter (str): Filter for evaluation names.
        status_filter (str): Filter for task statuses.

    Returns:
        pd.DataFrame: Processed task data.
    """
    query = """
    SELECT
        task.*,
        CASE
            WHEN executor_pid IS NULL AND result is NULL THEN 'initialized'
            WHEN result IS NULL THEN 'running'
            WHEN result LIKE '%RetryableSystemError%' THEN 'errored'
            ELSE 'completed'
        END AS status
    FROM task
    WHERE 1=1
    """
    if eval_name_filter != "All":
        query += f" AND eval_id = '{eval_name_filter}'"
    if status_filter != "All":
        query += f" AND {_STATUSES[status_filter]}"
    # query += " LIMIT 100"

    cursor = conn.execute(query)
    task_data = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
    task_data["task"] = task_data["task"].apply(lambda x: str(dill.loads(x)))
    task_data["result"] = task_data["result"].apply(lambda x: str(_load_result(x)))

    task_data["eval_name"] = task_data["eval_id"].apply(
        lambda x: eval_data[eval_data["run_id"] == x]["name"].values[0]
    )
    # Move eval_name to be the first column
    eval_name_column = task_data.pop("eval_name")
    task_data.insert(0, "eval_name", eval_name_column)
    if eval_name_filter != "All":
        task_data = task_data[task_data["eval_name"] == eval_name_filter]

    task_data["elapsed"] = (
        pd.to_datetime(task_data["end_time"].fillna(pd.Timestamp.now(tz=timezone.utc)))
        - pd.to_datetime(task_data["start_time"])  # type: ignore
    ).dt.total_seconds()

    return task_data


def main() -> None:
    import matplotlib.pyplot as plt
    import streamlit as st

    st.set_page_config(layout="wide")

    st.title("Monitor")

    folder = database_dir()
    db_files = sorted(
        [f for f in os.listdir(folder) if f.endswith(".db")],
        reverse=True,
    )
    db_options = [f"{f}" for f in db_files]  # List all .db files in the folder with creation date

    selected_option = st.selectbox("Select Database (by pid of main process)", db_options)

    if not selected_option:
        return
    selected_db = folder / db_files[db_options.index(selected_option)]
    st.write(f"Open with: `sqlite3 {selected_db}`")
    if not selected_db:
        return

    st.subheader("Evals")
    with _monitor_conn(folder / selected_db) as conn:
        eval_data = _fetch_table_data("eval", conn)
        # task_data = _fetch_table_data("task", conn)
        executor_data = _fetch_table_data("executor", conn)

    # Calculate percent_complete for each eval
    st.dataframe(eval_data)

    st.subheader("Running executors")
    executor_data["aiomonitor_cmd"] = executor_data["aiomonitor_host"].apply(
        lambda x: f"python3 -m aiomonitor.cli -H {x.split(':')[0]} -p {x.split(':')[1]}"
    )
    executor_data["py_spy"] = executor_data["pid"].apply(lambda x: f"py-spy dump --pid {x}")

    st.dataframe(executor_data)

    st.subheader("Tasks")

    eval_name_filter = st.selectbox(
        "Filter by run id", options=["All"] + list(eval_data["run_id"].unique())
    )
    eval_constraint = " AND eval_id = '{eval_name_filter}'" if eval_name_filter != "All" else ""

    # Add a filter for status
    status_filter = (
        st.selectbox(
            "Filter by status", options=["All", "initialized", "running", "errored", "completed"]
        )
        or "All"
    )

    # Add filter for the state column in the dataframe
    with _monitor_conn(folder / selected_db) as conn:
        task_data = _load_task_data(conn, eval_data, eval_name_filter, status_filter)

    st.dataframe(task_data.head(100))
    st.write("(first 100 rows)")

    with _monitor_conn(folder / selected_db) as conn:
        num_init = conn.execute(
            f"SELECT COUNT(*) FROM task WHERE executor_pid IS NULL AND result IS NULL {eval_constraint}"
        ).fetchone()[0]
        num_running = conn.execute(
            f"SELECT COUNT(*) FROM task WHERE executor_pid IS NOT NULL AND result IS NULL {eval_constraint}"
        ).fetchone()[0]
        num_completed = conn.execute(
            f"SELECT COUNT(*) FROM task WHERE result IS NOT NULL {eval_constraint}"
        ).fetchone()[0]
        num_total = conn.execute(
            f"SELECT COUNT(*) FROM task WHERE 1=1 {eval_constraint}"
        ).fetchone()[0]
        assert num_init + num_running + num_completed == num_total

        # Compute histogram of task completion rate per minute
        cursor = conn.execute(
            """
            select strftime("%s", end_time) as end_time, eval_id, eval.name as eval_name from task join eval on task.eval_id = eval.run_id where end_time is not null
            """
            + (f" AND eval_id = '{eval_name_filter}'" if eval_name_filter != "All" else "")
        )
        completion_rate_data = cursor.fetchall()

    st.subheader("Graphs")
    st.write(
        f"num_init: {num_init}, num_running: {num_running}, num_completed: {num_completed}, num_total: {num_total}"
    )

    completion_rate_df = pd.DataFrame(
        completion_rate_data, columns=["end_time", "eval_id", "eval_name"]
    )
    col1, col2 = st.columns(2)
    with col1:
        # Convert end_time to datetime and localize to Pacific Time
        completion_rate_df["end_time"] = pd.to_datetime(
            completion_rate_df["end_time"], unit="s", origin="unix"
        )

        # Plot the histogram of task completion rate per minute
        fig, ax = plt.subplots(figsize=(8, 4))
        # Convert end_time to Pacific Time
        completion_rate_df["end_time_pacific"] = (
            completion_rate_df["end_time"].dt.tz_localize("UTC").dt.tz_convert("US/Pacific")
        )

        # Plot histogram colored by eval_id
        for _eval_id, group in completion_rate_df.groupby("eval_id"):
            ax.hist(
                group["end_time_pacific"],
                bins=pd.date_range(  # type: ignore
                    start=completion_rate_df["end_time_pacific"].min(),
                    end=completion_rate_df["end_time_pacific"].max(),
                    freq="T",
                ),
                histtype="step",
                alpha=0.5,
                label=f"{group['eval_name'].iloc[0]}",
            )

        ax.set_xlabel("Time (Pacific Time)")
        ax.set_ylabel("Tasks per minute")
        ax.set_title("Task completion rate")
        ax.grid(True)
        plt.xticks(rotation=45)
        ax.legend(title="Eval name")
        st.pyplot(fig, use_container_width=True)

    with col2:
        status_counts = [
            ("initialized", num_init),
            ("running", num_running),
            ("completed", num_completed),
        ]
        status_labels = [row[0] for row in status_counts]
        status_sizes = [row[1] for row in status_counts]
        fig, ax = plt.subplots(figsize=(2, 2))  # Set the figure size to 300px by 300px
        ax.pie(
            status_sizes,
            labels=status_labels,
            # TODO(kevinliu) why does this round weirdly?
            autopct=lambda p: f"{p:.1f}%\n({int(p * sum(status_sizes) / 100)})",
        )
        ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
        st.pyplot(fig, use_container_width=False)
        # Add a filter for eval_name


if __name__ == "__main__":
    main()
