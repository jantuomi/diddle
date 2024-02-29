from dotenv import load_dotenv
load_dotenv()

import datetime
import os
from user_agents import parse as parse_user_agent
from dataclasses import dataclass
from flask import Flask, render_template, redirect, request, make_response
from flask_compress import Compress

app = Flask(__name__)
Compress(app)

import db
import email_client

BASE_URL = os.environ["BASE_URL"]

@dataclass
class ChoicesByVoter:
  name: str
  votes: list[bool]

TITLE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 1000
AUTHOR_NAME_MAX_LENGTH = 100
AUTHOR_EMAIL_MAX_LENGTH = 100
VOTER_NAME_MAX_LENGTH = 100

def voter_selection_on_choice(voter_name: str, choice: db.Choice) -> int | None:
  for vote in choice.votes:
    if vote.voter_name == voter_name:
      return vote.value
  return None

def validation_error(message: str):
  return render_template("error.html.j2", error=message), 400

@app.route("/")
def hello_world():
  created_poll_codes = []
  for k, _ in request.cookies.items():
    if k.startswith("diddle_manage_code_"):
      created_poll_codes.append(k.replace("diddle_manage_code_", ""))

  created_polls = db.get_polls_by_codes(created_poll_codes) if len(created_poll_codes) > 0 else []

  return render_template('index.html.j2',
                         created_polls=created_polls)

@app.post("/poll/create")
def create():
  form = request.form

  if "title" not in form or len(form["title"]) == 0:
    return validation_error("Title is required")
  if len(form["title"]) > TITLE_MAX_LENGTH:
    return validation_error(f"Title must be {TITLE_MAX_LENGTH} characters or fewer")
  if "description" in form and len(form["description"]) > DESCRIPTION_MAX_LENGTH:
    return validation_error(f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer")
  if "author_name" not in form or len(form["author_name"]) == 0:
    return validation_error("Author name is required")
  if len(form["author_name"]) > AUTHOR_NAME_MAX_LENGTH:
    return validation_error(f"Author name must be {AUTHOR_NAME_MAX_LENGTH} characters or fewer")
  if "author_email" in form and len(form["author_email"]) > AUTHOR_EMAIL_MAX_LENGTH:
    return validation_error(f"Author email must be {AUTHOR_EMAIL_MAX_LENGTH} characters or fewer")

  choices = []
  poll = db.create_poll(
    form["title"],
    form["description"],
    form["author_name"],
    form["author_email"],
    choices,
  )

  email_client.send_poll_created_email_if_enabled(poll_id=poll.id)

  resp = make_response(
    redirect(f"/manage/{poll.manage_code}")
  )
  resp.set_cookie(f"diddle_manage_code_{poll.manage_code}", "1",
                  samesite="Strict", secure=False)
  return resp


VoterNameChoiceIdPair = tuple[str, str]
@app.get("/poll/<id>")
def poll(id):
  poll = db.get_poll(id)
  if poll is None:
    return "Poll not found", 404

  display_mode_cookie = request.cookies.get("diddle_display_mode")
  if display_mode_cookie is None:
    user_agent = parse_user_agent(request.user_agent.string)
    if user_agent.is_mobile or user_agent.is_tablet:
      display_mode = "list"
    else:
      display_mode = "table"
  else:
    display_mode = display_mode_cookie

  voter_names_set: set[str] = set()
  selections: dict[VoterNameChoiceIdPair, int] = {}
  for choice in poll.choices:
    for vote in choice.votes:
      selections[(vote.voter_name, choice.id)] = vote.value
      voter_names_set.add(vote.voter_name)

  voter_names = list(voter_names_set)
  voter_names.sort()

  resp = make_response(
    render_template("poll.html.j2",
                    poll=poll,
                    selections=selections,
                    choices=poll.choices,
                    voter_names=voter_names,
                    now=datetime.datetime.now(),
                    display_mode=display_mode))

  resp.set_cookie("diddle_display_mode", display_mode,
                  samesite="Lax", secure=False)
  return resp


@app.post("/poll/<id>/vote")
def vote_poll(id):
  form = request.form
  if "voter_name" not in form or len(form["voter_name"]) == 0:
    return validation_error("Voter name is required")
  if len(form["voter_name"]) > VOTER_NAME_MAX_LENGTH:
    return validation_error(f"Voter name must be {VOTER_NAME_MAX_LENGTH} characters or fewer")

  poll = db.get_poll(id)
  if poll is None:
    return validation_error("Poll not found")

  voter_name: str = form["voter_name"]

  selections: dict[str, int] = {}
  for choice in poll.choices:
    selections[choice.id] = 0

  for k in form.keys():
    if k.startswith("choice_"):
      choice_id = k.replace("choice_", "")
      selections[choice_id] = 1

  db.vote_poll(id, voter_name, selections)

  email_client.send_participation_email_if_enabled(poll_id=id, voter_name=voter_name)

  return redirect(f"/poll/{id}")

@app.post("/manage/<code>/update_info")
def update_poll_info(code):
  form = request.form

  if "title" not in form or len(form["title"]) == 0:
    return validation_error("Title is required")
  if len(form["title"]) > TITLE_MAX_LENGTH:
    return validation_error(f"Title must be {TITLE_MAX_LENGTH} characters or fewer")
  if "description" in form and len(form["description"]) > DESCRIPTION_MAX_LENGTH:
    return validation_error(f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer")
  if "author_name" not in form or len(form["author_name"]) == 0:
    return validation_error("Author name is required")
  if len(form["author_name"]) > AUTHOR_NAME_MAX_LENGTH:
    return validation_error(f"Author name must be {AUTHOR_NAME_MAX_LENGTH} characters or fewer")
  if "author_email" in form and len(form["author_email"]) > AUTHOR_EMAIL_MAX_LENGTH:
    return validation_error(f"Author email must be {AUTHOR_EMAIL_MAX_LENGTH} characters or fewer")

  db.update_poll_info(
    code,
    form["title"],
    form["description"],
    form["author_name"],
    form["author_email"],
  )

  return redirect(f"/manage/{code}")

@app.post("/manage/<code>/add_choice")
def add_choice(code):
  form = request.form
  if "start_datetime" not in form or len(form["start_datetime"]) == 0:
    return validation_error("Start datetime is required")
  if "end_datetime" not in form or len(form["end_datetime"]) == 0:
    return validation_error("End datetime is required")
  if form["start_datetime"] >= form["end_datetime"]:
    return validation_error("Start datetime must be before end datetime")

  db.add_choice_to_poll(
    code,
    form["start_datetime"],
    form["end_datetime"],
  )

  return redirect(f"/manage/{code}")

@app.post("/manage/<code>/delete_choice/<choice_id>")
def delete_choice(code, choice_id):
  poll = db.get_poll_by_code(code)
  if poll is None:
    return "Poll not found", 404

  db.delete_choice(choice_id)

  return redirect(f"/manage/{code}")

@app.get("/manage/<code>")
def manage(code):
  poll = db.get_poll_by_code(code)
  if poll is None:
    return validation_error("Poll not found")

  last_choice_id = poll.choices[-1].id if len(poll.choices) > 0 else None
  resp = make_response(
    render_template("manage.html.j2",
                    poll=poll,
                    last_choice_id=last_choice_id))
  resp.set_cookie(f"diddle_manage_code_{code}", "1",
                  samesite="Strict", secure=False)
  return resp

@app.post("/manage/<code>/delete")
def delete_poll(code):
  poll = db.get_poll_by_code(code)
  return render_template("poll_confirm_delete.html.j2", poll=poll)

@app.post("/manage/<code>/confirm_delete")
def confirm_delete_poll(code):
  db.delete_poll(code)
  resp = make_response(redirect("/"))
  resp.set_cookie(f"diddle_manage_code_{code}", "", expires=0,
                  samesite="Strict", secure=False)
  return resp

@app.post("/options/toggle_display_mode")
def toggle_display_mode():
  poll_id = request.form["poll_id"]
  redirect_url = f"/poll/{poll_id}"
  display_mode = request.cookies.get("diddle_display_mode", "table")
  if display_mode == "table":
    display_mode = "list"
  else:
    display_mode = "table"

  resp = make_response(redirect(redirect_url))
  resp.set_cookie("diddle_display_mode", display_mode,
                  samesite="Lax", secure=False)
  return resp
