import logging
import os
import sys

import praw

SUB_NAME = os.environ["SUB_NAME"]
MIN_IMAGE_WIDTH_PX = 4000  # 470 DPI
NUM_POSTS_TO_PROCESS = 10
REMOVAL_MESSAGE_SUBJECT = "LOW QUALITY IMAGE"

REMOVAL_COMMENT = """
# Post Removed: Low Quality Image
\n
# Image Resolution Detected: {dpi} DPI
\n
---
**Hi /u/{author}, please follow the instructions below and submit a higher quality image in a new post.**  
\n
---
\n
1. Export your resume as a [**PDF file**](https://www.adobe.com/uk/acrobat/resources/google-doc-to-pdf.html).  
\n
2. Convert it to a **[600 DPI](https://www.adobe.com/uk/creativecloud/photography/discover/dots-per-inch-dpi-resolution.html) PNG file** using https://www.cleverpdf.com/pdf-to-images. https://imgur.com/RxxYFQe     
\n
3. On **[DESKTOP (NEW.REDDIT)](https://new.reddit.com/r/{sub}/submit)**, insert the PNG file into a **[TEXT SUBMISSION](https://imgur.com/8iik4YP)**.  
\n
---
\n
**Please do not:**  
\n
* Take a picture of your resume with your phone camera  
\n
* Take a screenshot of your resume  
\n
* Crop out your margins  
\n
* Upload a dark mode version of your resume  
\n
---
"""

REMOVAL_MESSAGE = """
**please follow the instructions below and submit a higher quality image in a new post.**  
\n
# Image Resolution Detected: {dpi} DPI
\n
---
\n
1. Export your resume as a [**PDF file**](https://www.adobe.com/uk/acrobat/resources/google-doc-to-pdf.html).  
\n
2. Convert it to a **[600 DPI](https://www.adobe.com/uk/creativecloud/photography/discover/dots-per-inch-dpi-resolution.html) PNG file** using https://www.cleverpdf.com/pdf-to-images. https://imgur.com/RxxYFQe     
\n
3. On **[DESKTOP (NEW.REDDIT)](https://new.reddit.com/r/{sub}/submit)**, insert the PNG file into a **[TEXT SUBMISSION](https://imgur.com/8iik4YP)**.  
\n
---
\n
**Please do not:**  
\n
* Take a picture of your resume with your phone camera  
\n
* Take a screenshot of your resume  
\n
* Crop out your margins  
\n
* Upload a dark mode version of your resume  
\n
---
"""


def setup_logger() -> None:
    logging.basicConfig(
        format="[%(asctime)s] %(message)s",
        datefmt="%m-%d %I:%M",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("logs.txt", mode="a"),
            logging.StreamHandler(),
        ],
    )


def create_reddit_instance() -> praw.Reddit:
    try:
        reddit = praw.Reddit(
            username=os.environ["USERNAME"],
            password=os.environ["PASSWORD"],
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            user_agent=os.environ["USER_AGENT"],
            ratelimit_seconds=600,
        )

    except Exception as e:
        logging.error("Failed to authenticate: %s", e)
        sys.exit()

    return reddit


def extract_width(selftext: str) -> int:
    try:
        extracted_string = selftext.split("width=")[1].split("&")[0]
        width = int(extracted_string)
        return int(width)

    except IndexError:
        return -1


def convert_to_dpi(image_width: int) -> int:
    return round(image_width / 8.5)


def reject(submission: praw.models.Submission, image_width: int) -> None:
    dpi_value = convert_to_dpi(image_width)
    submission.mod.remove(spam=False)
    submission.mod.flair(
        text="Post Removed: Low Quality Image",
        css_class="removed",
        flair_template_id="7e1d0b6c-b178-11ee-866f-b61c7ef1fdc8",
    )
    submission.mod.lock()
    removal_comment_with_author = REMOVAL_COMMENT.format(
        author=submission.author, sub=SUB_NAME, dpi=dpi_value
    )
    removal_message_with_subreddit_name = REMOVAL_MESSAGE.format(
        sub=SUB_NAME, dpi=dpi_value
    )
    submission.mod.send_removal_message(
        type="public_as_subreddit",
        message=removal_comment_with_author,
    )
    submission.mod.send_removal_message(
        type="private",
        title=REMOVAL_MESSAGE_SUBJECT,
        message=removal_message_with_subreddit_name,
    )
    logging.info("REJECT, %s, %d, %s", submission.id, image_width, submission.author)


def approve(submission: praw.models.Submission, image_width: int) -> None:
    submission.mod.approve()
    logging.info("APPROVE, %s, %d, %s", submission.id, image_width, submission.author)


def process(submission: praw.models.Submission) -> None:
    if submission.approved:
        return

    if submission.link_flair_text in {"Question", "Success Story!", "Meta"}:
        return

    image_width = extract_width(submission.selftext)

    if image_width == -1:
        logging.error(
            "UNABLE TO EXTRACT WIDTH FROM BODY TEXT, %s, %s",
            submission.id,
            submission.author,
        )

    elif image_width < MIN_IMAGE_WIDTH_PX:
        reject(submission, image_width)

    else:
        approve(submission, image_width)


if __name__ == "__main__":
    setup_logger()
    reddit = create_reddit_instance()
    subreddit = reddit.subreddit(SUB_NAME)

    for submission in subreddit.new(limit=NUM_POSTS_TO_PROCESS):
        process(submission)
