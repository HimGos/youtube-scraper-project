# -- Required Libraries --
from __future__ import unicode_literals
from selenium import webdriver
from selenium.webdriver.common.by import By
from googleapiclient.discovery import build
import time
import pymongo
import pymysql
from flask import Flask, render_template, request
import os
from waitress import serve
import logging as lg
from flask_cors import CORS, cross_origin


# -- Configuring Logger --
lg.basicConfig(filename="app.log", level=lg.INFO, format='%(name)s - %(levelname)s - %(message)s')


app = Flask(__name__)

@app.route('/')
@cross_origin()
def index():
    return render_template("index.html")


# API key from YouTube Data API
api_key = 'AIzaSyD4zIUOFHpX5HgP5jilgQp7rmnkzGv4i8Q'
youtube = build('youtube', 'v3', developerKey=api_key)


# -- Fetching Data from YouTube --

@app.route("/content", methods=["POST"])
@cross_origin()
def content():

    """ This function allows us to fetch data like urls, title, likes, comment count & thumbnail url
        from YouTube using webdriver. Further, push the data into MySQL"""

    if request.method == "POST":
        try:

            """ Links of YouTube Videos"""
            channel_username = request.form.get('content').replace(" ", "")
            lg.info("Successfully fetched channel username from index form!")

            # driver = webdriver.Chrome()
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)

            driver.get("https://www.youtube.com/" + channel_username + "/videos")

            print("Web Driver Running... Fetching Data...")

            # Loop to scroll page 10 times to get approx 60 videos.
            for i in range(10):
                driver.execute_script("window.scrollTo(0,(window.pageYOffset+300))")
                time.sleep(0.5)

            all_links = []

            for video in driver.find_elements(By.ID, "thumbnail"):
                if video.get_attribute('href') == None:
                    continue
                elif "shorts" in video.get_attribute('href'):
                    continue
                all_links.append(video.get_attribute('href'))

            if len(all_links) == 0:
                return render_template("404.html")

            else:

                """ Titles, Like Count, Comment Count, Thumbnail Links """

                title = []            # Required for MySQL
                likes = []            # Required for MySQL
                total_comments = []   # Required for MySQL
                thumbnails = []       # Required for MySQL

                full_data = []        # Required for flask's render template
                serial_no = 0

                for link in all_links[:50]:
                    video_id = ''.join(link.split('=')[1])

                    yt_request = youtube.videos().list(
                        part='statistics, snippet',
                        id=video_id)

                    response = yt_request.execute()

                    # Fetching Titles
                    titles = response['items'][0]['snippet']['title']
                    title.append(titles)

                    # Fetching Likes Count
                    likes_count = response['items'][0]['statistics']['likeCount']
                    likes.append(likes_count)

                    # Fetching Comment Count
                    comment_count = response['items'][0]['statistics']['commentCount']
                    total_comments.append(comment_count)

                    # Fetching Thumbnail Links
                    thumbnails_link = response['items'][0]['snippet']['thumbnails']['medium']['url']
                    thumbnails.append(thumbnails_link)

                    serial_no += 1

                    d = {"Serial No": serial_no, "Title": titles, "LikesCount": likes_count,
                         "CommentCount": comment_count, "Thumbnails": thumbnails_link, "VideoID": video_id}

                    full_data.append(d)


                # -- Pushing Data in MySQL Table -- Commented Out! --

                """
                try:
                    lg.info("Setting up mysql connection...")
                    mydb = pymysql.connect(host="localhost",
                                           user="YourUsername",
                                           passwd="YourPassword")

                    cursor = mydb.cursor()
                    print("Connected to MySQL Server!")

                    cursor.execute("CREATE DATABASE IF NOT EXISTS ytproject")
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS ytproject.{channel_username}("
                                   "Serial INT,"
                                   "Title VARCHAR(255),"
                                   "Likes VARCHAR(10),"
                                   "Total_Comments VARCHAR(10),"
                                   "Video_Link VARCHAR(255),"
                                   "Thumbnail VARCHAR(255)"
                                   ")")

                    # Collecting all records in a single list, grouped as tuple
                    record = []
                    for i in range(50):
                        element = []
                        element.append(i + 1)
                        element.append(title[i])
                        element.append(likes[i])
                        element.append(total_comments[i])
                        element.append(all_links[i])
                        element.append(thumbnails[i])
                        element = tuple(element)
                        record.append(element)

                    # Inserting Data into mysql table at once.
                    print("Inserting Data into MySQL Table...")
                    sql_query = f"INSERT INTO ytproject.{channel_username}(Serial, Title, Likes, Total_Comments, Video_Link, Thumbnail) " \
                                f"VALUES(%s, %s, %s, %s, %s, %s)"

                    cursor.executemany(sql_query, record)

                    mydb.commit()
                    mydb.close()

                    print("Records adding successfully into Mysql Table")
                    lg.info("Successfully pushed data into MySQL table.")

                except Exception as err:
                    print("Something incorrect: ", err)
                    lg.error("Couldn't push data in MySQL")
                    """

                lg.info("Successfully got all values in content function")
                return render_template("content.html", data=full_data), 200

        except Exception as err:
            print(err)
            lg.error("Error in content function")
            return "Something is Wrong!"

    else:
        lg.error("POST method error in content function.")
        return render_template("index.html")


@app.route("/comments/<video_id>")
@cross_origin()
def comments(video_id):

    """ This function allows us to fetch the comment and authors of particular video requested on previous page.
        Further we can push the data on MongoDB."""

    try:

        comm_request = youtube.commentThreads().list(
            part='snippet', videoId=video_id)
        comm_response = comm_request.execute()

        vid_comments = []

        count = 0
        for item in comm_response['items']:

            commenters = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            comments = item['snippet']['topLevelComment']['snippet']['textDisplay']
            count += 1
            comment_data = {"SerialNo": count, "Author": commenters, "Comment": comments}

            vid_comments.append(comment_data)


        # -- Pushing comments in MongoDB -- Commented Out! --

        """
        try:
            print("Setting up MongoDB Connection...")
            client = pymongo.MongoClient(
                "Your Mongo Connection URL")
            db = client.test
            print("Connected to Mongodb")

            database = client['yt_data_project']
            coll = database['Comments']

            print("Inserting Data in MongoDB...")

            coll.insert_many(vid_comments)
            print("Inserting Data in MongoDB successfully!")

        except Exception as err:
            lg.error("Error pushing data in MongoDB")
            print("Something incorrect: ", err)
        """

        print(vid_comments)
        lg.info("Successfully fetched all comments in comments function")

        return render_template("comments.html", vid_comments=vid_comments)


    except Exception as err:
        lg.error("comments function didn't work!")
        print(err)
        return "Something is Wrong!"


@app.route('/download/<video_id>')
@cross_origin()
def download(video_id):

    """ This function will allow us to view and download video. We download video using code below
        and view video using YouTube iframe on html. """

    try:

        driver = webdriver.Chrome()
        # Heading to website from where we can download video
        driver.get("https://en.savefrom.net/210/")
        element = driver.find_element(By.ID, "sf_url")
        # send url of video
        element.send_keys("https://www.youtube.com/watch?v=" + video_id)
        # submit button click
        element.submit()

        time.sleep(4)

        # clicking the href of download button.
        element1 = driver.find_element(By.LINK_TEXT, "Download")
        # Finally, click on it.
        element1.click()

        lg.info("Successfully downloaded video in download function")
        return render_template("download.html", video_id=video_id)

    except Exception as err:
        lg.error("download function didn't work")
        print(err)
        return err


if __name__ == "__main__":
    # app.run(debug=True)
    app.debug = False
    serve(app)


