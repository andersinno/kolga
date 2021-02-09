from typing import TYPE_CHECKING, Any, List, TypedDict

if TYPE_CHECKING:
    from kolga.libs.project import Project


class _SlackMessageField(TypedDict, total=False):
    type: str
    text: str


class _SlackMessageBody(TypedDict, total=False):
    type: str
    fields: List[_SlackMessageField]


def new_environment_message(environment_track: str, project: "Project") -> List[Any]:
    # Import settings in function to not have circular imports
    from kolga.settings import settings

    message: List[Any] = []
    title_section = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*New {environment_track} deployment for {project.verbose_name}*",
        },
    }
    body_section: _SlackMessageBody = {"type": "section", "fields": []}

    if project.url:
        body_section["fields"].append(
            {"type": "mrkdwn", "text": f"*:link: URL:*\n <{project.url}|Link>"}
        )

    if settings.PR_URL and settings.PR_TITLE:
        body_section["fields"].append(
            {
                "type": "mrkdwn",
                "text": f"*:pick: Pull/Merge Request:*\n <{settings.PR_URL}|{settings.PR_TITLE}>",
            }
        )

    if settings.JOB_ACTOR:
        body_section["fields"].append(
            {
                "type": "mrkdwn",
                "text": f"*:bust_in_silhouette: Pipeline creator*\n{settings.JOB_ACTOR}",
            }
        )

    if settings.PR_ASSIGNEES:
        body_section["fields"].append(
            {
                "type": "mrkdwn",
                "text": f"*:busts_in_silhouette: Reviewers:*\n{settings.PR_ASSIGNEES}",
            }
        )

    message.append(title_section)
    message.append(body_section)

    return message
