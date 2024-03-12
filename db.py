import os
from typing import Literal
from dataclasses import dataclass
import datetime
import psycopg2
import uuid

BASE_URL = os.environ["BASE_URL"]

class DbContextManager:
  def __init__(self, db: "Db"):
    self.db = db

  def __enter__(self):
    self.cursor = self.db.get_cursor()
    return (self.db.conn, self.cursor)

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.cursor:
      self.cursor.close()
    # Return False to propagate exceptions, True to suppress them
    return False

class Db:
  MAX_RETRIES = 5

  def __init__(self):
    self.connect()

  def connect(self):
    self.conn = psycopg2.connect(
      host=os.getenv('DB_HOST', 'localhost'),
      database=os.getenv('DB_DATABASE', 'postgres'),
      port=os.getenv('DB_PORT', '5432'),
      user=os.getenv('DB_USER', 'postgres'),
      password=os.environ['DB_PASSWORD'])

  def get_cursor(self):
    for _ in range(self.MAX_RETRIES):
      try:
        return self.conn.cursor()
      except psycopg2.Error:
        self.connect()

    raise Exception(f"Failed to connect to database after {Db.MAX_RETRIES} retries.")

  def cursor(self):
    return DbContextManager(db=self)

db = Db()

@dataclass
class Vote:
  id: str
  poll_id: str
  choice_id: str
  voter_name: str
  value: int # 0 or 1
  manage_code: str

@dataclass
class Choice:
  id: str
  poll_id: str
  start_datetime: datetime.datetime
  end_datetime: datetime.datetime
  votes: list[Vote]

  def start_datetime_notz(self):
    return self.start_datetime.replace(tzinfo=None)

  def end_datetime_notz(self):
    return self.end_datetime.replace(tzinfo=None)

  def start_date_notz(self):
    return self.start_datetime.date()

  def end_date_notz(self):
    return self.end_datetime.date()

  def ends_on_same_day(self):
    return self.start_datetime.date() == self.end_datetime.date()

  def ends_at_same_datetime(self):
    return self.start_datetime.date() == self.end_datetime.date() \
       and self.start_datetime.time() == self.end_datetime.time()

  def votes_with_value(self, value: int) -> list[Vote]:
    return [vote for vote in self.votes if vote.value == value]

@dataclass
class Poll:
  id: str
  title: str
  description: str | None
  pub_date: datetime.datetime
  author_name: str
  author_email: str | None
  choices: list[Choice]
  manage_code: str
  is_whole_day: bool

  def pub_date_formatted_notz(self):
    date = self.pub_date.replace(tzinfo = None).strftime("%d.%m.%Y")
    time = self.pub_date.replace(tzinfo = None).strftime("%H:%M")
    return f"Created on {date} at {time}"

  def share_url(self):
    return f"{BASE_URL}/poll/{self.id}"

  def manage_url(self):
    return f"{BASE_URL}/manage/{self.manage_code}"

def tuple_to_poll(poll_t: tuple) -> Poll:
  return Poll(
    id=poll_t[0],
    title=poll_t[1],
    description=poll_t[2],
    pub_date=poll_t[3],
    author_name=poll_t[4],
    author_email=poll_t[5],
    manage_code=poll_t[6],
    is_whole_day=poll_t[7],
    choices=[]
  )

def tuple_to_choice(choice_t: tuple) -> Choice:
  return Choice(
    id=choice_t[0],
    poll_id=choice_t[1],
    start_datetime=choice_t[2],
    end_datetime=choice_t[3],
    votes=[]
  )

def tuple_to_vote(vote_t: tuple) -> Vote:
  return Vote(
    id=vote_t[0],
    poll_id=vote_t[1],
    choice_id=vote_t[2],
    voter_name=vote_t[3],
    value=vote_t[4],
    manage_code=vote_t[5]
  )

def get_poll(id: str):
  with db.cursor() as (conn, cur):
    try:
      cur.execute("SELECT * FROM polls WHERE id = %s", (id,))
      poll_t = cur.fetchone()
      if poll_t is None:
        return None

      poll = tuple_to_poll(poll_t)
      cur.execute("SELECT * FROM choices "
                  "WHERE poll_id = %s "
                  "ORDER BY start_datetime", (id,))
      choice_ts = cur.fetchall()

      cur.execute("SELECT * FROM votes "
                  "WHERE poll_id = %s "
                  "ORDER BY voter_name", (id,))
      vote_ts = cur.fetchall()

      for choice_t in choice_ts:
        choice = tuple_to_choice(choice_t)

        for vote_t in vote_ts:
          vote = tuple_to_vote(vote_t)
          if vote.choice_id == choice.id:
            choice.votes.append(vote)

        poll.choices.append(choice)

      conn.commit()
      return poll
    except Exception as e:
      conn.rollback()
      raise e

def create_poll(title: str,
                description: str | None,
                author_name: str,
                author_email: str | None,
                is_whole_day: bool):

  with db.cursor() as (conn, cur):
    try:
      cur.execute("INSERT INTO polls (title, description, author_name, author_email, whole_day)"
                  "VALUES (%s, %s, %s, %s, %s) RETURNING *",
                  (title, description, author_name, author_email, is_whole_day))
      poll_t = cur.fetchone()

      if poll_t is None:
        raise Exception("Failed to create poll")

      poll = tuple_to_poll(poll_t)

      conn.commit()
      return poll
    except Exception as e:
      conn.rollback()
      raise e

def vote_poll(poll_id: str, voter_name: str, selections: dict[str, int]) -> str | None:
  """Returns the manage code of the vote or None if the vote failed on unique constraint."""
  with db.cursor() as (conn, cur):
    try:
      manage_code = str(uuid.uuid4())
      for choice_id in selections:
        value = selections[choice_id]
        cur.execute("INSERT INTO votes (poll_id, voter_name, choice_id, value, manage_code)"
                    "VALUES (%s, %s, %s, %s, %s)",
                    (poll_id, voter_name, choice_id, value, manage_code))
      conn.commit()
      return manage_code
    except psycopg2.errors.UniqueViolation:
      conn.rollback()
      return None
    except Exception as e:
      conn.rollback()
      raise e

def get_poll_by_code(code: str) -> Poll | None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("SELECT id FROM polls WHERE manage_code = %s", (code,))
      poll_t = cur.fetchone()
      if poll_t is None:
        return None

      poll = get_poll(poll_t[0])
      conn.commit()
      return poll
    except Exception as e:
      conn.rollback()
      raise e

def update_poll_info(
    code: str,
    title: str,
    description: str | None,
    author_name: str,
    author_email: str | None,
    is_whole_day: bool,
  ) -> str | None:
  """Returns the id of the updated poll or None if not found."""
  with db.cursor() as (conn, cur):
    try:
      cur.execute("UPDATE polls SET title = %s, description = %s, author_name = %s, author_email = %s, whole_day = %s "
                  "WHERE manage_code = %s "
                  "RETURNING id",
                  (title, description, author_name, author_email, is_whole_day, code))
      changed = cur.fetchone()
      conn.commit()
      return changed[0] if changed else None
    except Exception as e:
      conn.rollback()
      raise e

def add_choice_to_poll(
    code,
    start_datetime,
    end_datetime,
  ) -> None:
  poll = get_poll_by_code(code)
  if poll is None:
    raise Exception(f"Poll not found for code: {code}")

  with db.cursor() as (conn, cur):
    try:
      cur.execute("INSERT INTO choices (poll_id, start_datetime, end_datetime)"
                  "VALUES (%s, %s, %s) "
                  "RETURNING id",
                  (poll.id, start_datetime, end_datetime))
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise e

def delete_choice(choice_id: str) -> None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("DELETE FROM choices WHERE id = %s", (choice_id,))
      cur.execute("DELETE FROM votes WHERE choice_id = %s", (choice_id,))
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise e

def get_polls_by_codes(codes: list[str]) -> list[Poll]:
  with db.cursor() as (conn, cur):
    try:
      codes_t = tuple(codes)
      cur.execute("SELECT * FROM polls "
                  "WHERE manage_code IN %s "
                  "ORDER BY pub_date DESC", (codes_t,))
      poll_ts = cur.fetchall()
      polls = [tuple_to_poll(poll_t) for poll_t in poll_ts]

      conn.commit()
      return polls
    except Exception as e:
      conn.rollback()
      raise e

def delete_poll(code: str) -> None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("DELETE FROM polls WHERE manage_code = %s", (code,))
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise e

def get_voter_name_by_manage_code(voter_manage_code: str) -> str | None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("SELECT voter_name FROM votes WHERE manage_code = %s", (voter_manage_code,))
      voter_name = cur.fetchone()
      conn.commit()
      return voter_name[0] if voter_name else None
    except Exception as e:
      conn.rollback()
      raise e

def delete_voter(voter_manage_code: str) -> None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("DELETE FROM votes WHERE manage_code = %s", (voter_manage_code,))
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise e

### Migrations

def ensure_migration_table_exists() -> None:
  with db.cursor() as (conn, cur):
    try:
      cur.execute("CREATE TABLE IF NOT EXISTS applied_migrations ("
                  "number INTEGER PRIMARY KEY"
                  ")")
      conn.commit()
    except Exception as e:
      conn.rollback()
      raise e

def ensure_migration_applied(number: int, migration_sql: str) -> bool:
  """Returns True if the migration was applied, False if it was already applied."""
  with db.cursor() as (conn, cur):
    try:
      cur.execute("SELECT * FROM applied_migrations WHERE number = %s", (number,))
      if cur.fetchone() is not None:
        return False

      cur.execute("INSERT INTO applied_migrations (number) VALUES (%s)", (number,))
      cur.execute(migration_sql)
      conn.commit()
      return True

    except Exception as e:
      conn.rollback()
      raise e
