import os
from typing import List, Optional, Tuple, cast
from dataclasses import dataclass
import datetime
import sqlite3
import uuid

BASE_URL = os.environ.get("BASE_URL", "http://localhost")
DB_PATH = os.environ.get("DB_PATH", "db.sqlite3")
DB_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class DbContextManager:
    def __init__(self, db: "Db"):
        self.db = db
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = self.db.connect()
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        conn: sqlite3.Connection = cast(sqlite3.Connection, self.conn)
        if exc_type:
            conn.rollback()
        else:
            conn.commit()

        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

class Db:
    def __init__(self):
        pass

    def connect(self):
        conn = sqlite3.connect(
            DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            isolation_level="IMMEDIATE",
        )
        conn.row_factory = sqlite3.Row
        return conn

    def cursor(self):
        return DbContextManager(db=self)

db = Db()

@dataclass
class Vote:
    id: str
    poll_id: str
    choice_id: str
    voter_name: str
    value: int  # 0 or 1
    manage_code: str

@dataclass
class Choice:
    id: str
    poll_id: str
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    votes: List[Vote]

    def start_datetime_notz(self) -> datetime.datetime:
        return self.start_datetime.replace(tzinfo=None)

    def end_datetime_notz(self) -> datetime.datetime:
        return self.end_datetime.replace(tzinfo=None)

    def start_date_notz(self) -> datetime.date:
        return self.start_datetime.date()

    def end_date_notz(self) -> datetime.date:
        return self.end_datetime.date()

    def ends_on_same_day(self) -> bool:
        return self.start_datetime.date() == self.end_datetime.date()

    def ends_at_same_datetime(self) -> bool:
        return self.start_datetime == self.end_datetime

    def votes_with_value(self, value: int) -> List[Vote]:
        return [vote for vote in self.votes if vote.value == value]

@dataclass
class Poll:
    id: str
    title: str
    description: Optional[str]
    pub_date: datetime.datetime
    author_name: str
    author_email: Optional[str]
    choices: List[Choice]
    manage_code: str
    is_whole_day: bool

    def pub_date_formatted_notz(self) -> str:
        date = self.pub_date.replace(tzinfo=None).strftime("%d.%m.%Y")
        time = self.pub_date.replace(tzinfo=None).strftime("%H:%M")
        return f"Created on {date} at {time}"

    def share_url(self) -> str:
        return f"{BASE_URL}/poll/{self.id}"

    def manage_url(self) -> str:
        return f"{BASE_URL}/manage/{self.manage_code}"

def tuple_to_poll(poll_t: Tuple) -> Poll:
    return Poll(
        id=poll_t[0],
        title=poll_t[1],
        description=poll_t[2],
        pub_date=datetime.datetime.strptime(poll_t[3], DB_DATE_FORMAT),
        author_name=poll_t[4],
        author_email=poll_t[5],
        manage_code=poll_t[6],
        is_whole_day=poll_t[7],
        choices=[]
    )

def tuple_to_choice(choice_t: Tuple) -> Choice:
    return Choice(
        id=choice_t[0],
        poll_id=choice_t[1],
        start_datetime=datetime.datetime.strptime(choice_t[2], DB_DATE_FORMAT),
        end_datetime=datetime.datetime.strptime(choice_t[3], DB_DATE_FORMAT),
        votes=[]
    )

def tuple_to_vote(vote_t: Tuple) -> Vote:
    return Vote(
        id=vote_t[0],
        manage_code=vote_t[1],
        poll_id=vote_t[2],
        choice_id=vote_t[3],
        voter_name=vote_t[4],
        value=vote_t[5],
    )

def get_poll(id: str) -> Optional[Poll]:
    with db.cursor() as (conn, cur):
        cur.execute("SELECT * FROM polls WHERE id = ?", (id,))
        poll_t = cur.fetchone()
        if poll_t is None:
            return None

        poll = tuple_to_poll(poll_t)
        cur.execute("SELECT * FROM choices WHERE poll_id = ? ORDER BY start_datetime", (id,))
        choice_ts = cur.fetchall()

        cur.execute("SELECT * FROM votes WHERE poll_id = ? ORDER BY voter_name", (id,))
        vote_ts = cur.fetchall()

        for choice_t in choice_ts:
            choice = tuple_to_choice(choice_t)

            for vote_t in vote_ts:
                vote = tuple_to_vote(vote_t)
                if vote.choice_id == choice.id:
                    choice.votes.append(vote)

            poll.choices.append(choice)

        return poll

def create_poll(title: str, description: Optional[str], author_name: str, author_email: Optional[str], is_whole_day: bool) -> Poll:
    with db.cursor() as (conn, cur):
        cur.execute("INSERT INTO polls (title, description, author_name, author_email, whole_day)"
                    "VALUES (?, ?, ?, ?, ?)"
                    "RETURNING *",
                    (title, description, author_name, author_email, is_whole_day))
        poll_t = cur.fetchone()

        if poll_t is None:
            raise Exception("Failed to create poll")

        return tuple_to_poll(poll_t)

def vote_poll(poll_id: str, voter_name: str, selections: dict[str, int]) -> Optional[str]:
    """Returns the manage code of the vote or None if the vote failed on unique constraint."""
    with db.cursor() as (conn, cur):
        manage_code = str(uuid.uuid4())
        for choice_id, value in selections.items():
            try:
                cur.execute("INSERT INTO votes (poll_id, voter_name, choice_id, value, manage_code) VALUES (?, ?, ?, ?, ?)",
                            (poll_id, voter_name, choice_id, value, manage_code))
            except sqlite3.IntegrityError:
                return None
        return manage_code

def get_poll_by_code(code: str) -> Optional[Poll]:
    with db.cursor() as (conn, cur):
        cur.execute("SELECT id FROM polls WHERE manage_code = ?", (code,))
        poll_t = cur.fetchone()
        if poll_t is None:
            return None

        return get_poll(poll_t[0])

def update_poll_info(code: str, title: str, description: Optional[str], author_name: str, author_email: Optional[str], is_whole_day: bool) -> Optional[str]:
    """Returns the id of the updated poll or None if not found."""
    with db.cursor() as (conn, cur):
        cur.execute(
            "UPDATE polls SET title = ?, description = ?, author_name = ?, author_email = ?, whole_day = ? WHERE manage_code = ?",
            (title, description, author_name, author_email, is_whole_day, code)
        )
        cur.execute("SELECT id FROM polls WHERE manage_code = ?", (code,))
        updated_poll = cur.fetchone()
        return updated_poll[0] if updated_poll else None

def add_choice_to_poll(code: str, start_datetime: str, end_datetime: str) -> None:
    poll = get_poll_by_code(code)
    if poll is None:
        raise Exception(f"Poll not found for code: {code}")

    with db.cursor() as (conn, cur):
        cur.execute("INSERT INTO choices (poll_id, start_datetime, end_datetime) VALUES (?, ?, ?)",
                    (poll.id, start_datetime, end_datetime))

def delete_choice(choice_id: str) -> None:
    with db.cursor() as (conn, cur):
        cur.execute("DELETE FROM choices WHERE id = ?", (choice_id,))
        cur.execute("DELETE FROM votes WHERE choice_id = ?", (choice_id,))

def get_polls_by_codes(codes: List[str]) -> List[Poll]:
    with db.cursor() as (conn, cur):
        query = "SELECT * FROM polls WHERE manage_code IN ({}) ORDER BY pub_date DESC".format(
            ",".join("?" for _ in codes)
        )
        cur.execute(query, codes)
        poll_ts = cur.fetchall()
        return [tuple_to_poll(poll_t) for poll_t in poll_ts]

def delete_poll(code: str) -> None:
    with db.cursor() as (conn, cur):
        cur.execute("DELETE FROM polls WHERE manage_code = ?", (code,))

def get_voter_name_by_manage_code(voter_manage_code: str) -> Optional[str]:
    with db.cursor() as (conn, cur):
        cur.execute("SELECT voter_name FROM votes WHERE manage_code = ?", (voter_manage_code,))
        voter_name = cur.fetchone()
        return voter_name[0] if voter_name else None

def delete_voter(voter_manage_code: str) -> None:
    with db.cursor() as (conn, cur):
        cur.execute("DELETE FROM votes WHERE manage_code = ?", (voter_manage_code,))

### Migrations

def ensure_migration_table_exists() -> None:
    with db.cursor() as (conn, cur):
        cur.execute("CREATE TABLE IF NOT EXISTS applied_migrations (number INTEGER PRIMARY KEY)")

def ensure_migration_applied(number: int, migration_sql: str) -> bool:
    """Returns True if the migration was applied, False if it was already applied."""
    with db.cursor() as (conn, cur):
        cur.execute("SELECT 1 FROM applied_migrations WHERE number = ?", (number,))
        if cur.fetchone() is not None:
            return False

        cur.execute("INSERT INTO applied_migrations (number) VALUES (?)", (number,))
        cur.executescript(migration_sql)
        return True
