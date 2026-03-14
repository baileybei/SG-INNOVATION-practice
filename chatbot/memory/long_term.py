"""
长期记忆：情绪相关数据（SQLite）
- emotion_log:     每轮对话情绪流水（全存，含 neutral 和 user_input）
- emotion_summary: 每日情绪汇总（23:59 定时任务写入，永久保留）
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "health_events.db"


class HealthEventStore:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(DB_PATH)) as conn:
            # 迁移：检测旧 schema（user_input 列缺失，或 user_id 仍为 PRIMARY KEY / UNIQUE），直接重建
            table_info = conn.execute("PRAGMA table_info(emotion_log)").fetchall()
            cols = {r[1] for r in table_info}
            need_recreate = False

            if cols:
                if "user_input" not in cols:
                    need_recreate = True
                else:
                    user_id_info = next((r for r in table_info if r[1] == "user_id"), None)
                    if user_id_info and user_id_info[5] == 1:
                        # user_id 仍是 PRIMARY KEY（旧 schema）
                        need_recreate = True
                    else:
                        for idx in conn.execute("PRAGMA index_list(emotion_log)").fetchall():
                            if idx[2] == 1:
                                idx_info = conn.execute(f"PRAGMA index_info({idx[1]})").fetchall()
                                if len(idx_info) == 1 and idx_info[0][2] == "user_id":
                                    need_recreate = True
                                    break

            if need_recreate:
                conn.execute("DROP TABLE IF EXISTS emotion_log")
                conn.execute("DROP INDEX IF EXISTS idx_emotion_log_user")

            # 情绪流水：每轮对话写一条，全量保留
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emotion_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       TEXT NOT NULL,
                    emotion_label TEXT NOT NULL,
                    user_input    TEXT NOT NULL DEFAULT '',
                    recorded_at   TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emotion_log_user "
                "ON emotion_log(user_id, recorded_at)"
            )
            # 每日情绪汇总：23:59 定时任务写入，永久保留
            conn.execute("""
                CREATE TABLE IF NOT EXISTS emotion_summary (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id  TEXT NOT NULL,
                    text     TEXT NOT NULL,
                    date     TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_emotion_summary_user "
                "ON emotion_summary(user_id, date)"
            )

    # ── emotion_log methods ────────────────────────────────────────

    def log_emotion(self, user_id: str, emotion_label: str, user_input: str) -> None:
        """每轮对话写入一条情绪记录（含 neutral）。"""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO emotion_log (user_id, emotion_label, user_input, recorded_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id, emotion_label, user_input, datetime.now().isoformat()),
            )

    def get_today_emotions(self, user_id: str) -> list:
        """获取今日所有情绪记录（供 23:59 汇总用）。"""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT emotion_label, user_input, recorded_at FROM emotion_log "
                "WHERE user_id=? AND recorded_at LIKE ? ORDER BY recorded_at",
                (user_id, f"{today}%"),
            ).fetchall()
        return [
            {"emotion_label": r[0], "user_input": r[1], "recorded_at": r[2]}
            for r in rows
        ]

    def get_today_emotion_user_ids(self) -> list:
        """获取今日有情绪记录的所有 user_id。"""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT DISTINCT user_id FROM emotion_log WHERE recorded_at LIKE ?",
                (f"{today}%",),
            ).fetchall()
        return [r[0] for r in rows]

    # ── emotion_summary methods ────────────────────────────────────

    def save_emotion_summary(self, user_id: str, text: str, date: str) -> None:
        """写入每日情绪汇总（由 23:59 定时任务调用）。"""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO emotion_summary (user_id, text, date) VALUES (?, ?, ?)",
                (user_id, text, date),
            )

    def get_emotion_summaries(self, user_id: str, days: int = 14) -> list:
        """获取近 N 天情绪摘要，按日期倒序最多 5 条。"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                "SELECT text, date FROM emotion_summary "
                "WHERE user_id=? AND date>=? "
                "ORDER BY date DESC LIMIT 5",
                (user_id, cutoff),
            ).fetchall()
        return [{"text": r[0], "date": r[1]} for r in rows]

    def format_emotion_summary_for_llm(self, user_id: str, days: int = 14) -> str:
        """将近期情绪摘要格式化为叙事段落注入 companion/expert prompt。"""
        summaries = self.get_emotion_summaries(user_id, days)
        if not summaries:
            return ""
        lines = ["【患者近期情绪背景】"]
        for s in summaries:
            lines.append(f"- {s['date']}：{s['text']}")
        return "\n".join(lines)


# ── 单例 ─────────────────────────────────────────────────────────
_store: "HealthEventStore | None" = None


def get_health_store() -> HealthEventStore:
    global _store
    if _store is None:
        _store = HealthEventStore()
    return _store
