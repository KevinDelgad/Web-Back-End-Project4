### Backend Project 4

| Group 4            |
| -------------------|
| Carter Loya        |
| Kenny Tran         |
| Kevin Delgado      |
| Sravani Kallempudi |

##### HOW TO RUN THE PROJECT
An Error was carried over from project 3 which does not allow for tuffix-vm tests to work.
Due to time constraints we were unable to fix this. Instead please use 127.0.0.1 to test.
Here is a list of commands which you can use to test our project:
http POST http://127.0.0.1:5000/registration username=<username> password=<password>
http --auth <username>:<password> POST http://127.0.0.1:5100/newgame
http POST http://127.0.0.1:5100/subscribe url=<url>
http --auth <username>:<password>  PUT http://127.0.0.1:5100/addguess gameid=<gameid> word=<word>

1. Copy the contents of our [nginx config file] into a new file within `/etc/nginx/sites-enabled` called `nginxconfig`. 
   Assuming the nginx service is already running, restart the service using `sudo service nginx restart`.

Nginx Config:

```
server {
    listen 80;
    listen [::]:80;

    server_name tuffix-vm;

    location /registration {
        proxy_pass http://127.0.0.1:5000/registration;
    }

    location /newgame {
        auth_request /auth;
        proxy_pass http://gameservice;
    }

    location /addguess {
            auth_request /auth;
            proxy_pass http://gameservice;
    }

    location /allgames {
            auth_request /auth;
            proxy_pass http://gameservice;
    }

    location /onegame {
        auth_request /auth;
        proxy_pass http://gameservice;
    }


    location = /auth {
           internal;
           proxy_pass http://127.0.0.1:5000/login;
    }

}

upstream gameservice {
    server 127.0.0.1:5100;
    server 127.0.0.1:5200;
    server 127.0.0.1:5300;
}
```

2. Initialize the folder stucture within the project folder and install redis if you have not previously installed

   ```c
      // step 1. give the script permissions to execute
      chmod +x ./bin/folder.sh

      // step 2. run the script
      ./bin/folder.sh
   ```

   ```c
      // step 3. install the required
      pip install redis
      pip install httpx
   ```

3. Start the API

   ```c
      foreman start
      // NOTE: if there's an error upon running this where it doesn't recognize hypercorn, log out of Ubuntu and log back in.
   ```

4. Initialize the databases within the project folder

   ```c
      // step 1. give the script permissions to execute
      chmod +x ./bin/init.sh

      // step 2. run the script
      ./bin/init.sh
   ```

5. Populate the word databases

   ```c
      python3 dbpop.py
   ```

6. Set up Crontab

   ```To set up the crontab properly, copy the contents of our crontab.txt file,
      as long as you have the rq worker installed, their should be no issues.
      The cronjob process will be recorded in the cronlog provided by our repository.
      You can also copy the cron command right here:
      */10 * * * * rq requeue --all --queue default >> /home/student/Downloads/Web-Back-End-Project4-addworker/cronlog.log 2>&1

   ```


7. Test all the endpoints using httpie
   - user
      - register account: `http POST http://127.0.0.1:5000/registration username="yourusername" password="yourpassword"`

       Sample Output:
       ```
      {
         "id": 3,
         "password": "yourusername",
         "username": "yourpassword"
      }
      ```
     - login {Not accesible}: 'http --auth yourusername:yourpassword GET http://127.0.0.1:5000/login'
     Sample Output:
     ```
      HTTP/1.1 404 Not Found
      Connection: keep-alive
      Content-Encoding: gzip
      Content-Type: text/html
      Date: Fri, 18 Nov 2022 21:04:31 GMT
      Server: nginx/1.18.0 (Ubuntu)
      Transfer-Encoding: chunked

      <html>
      <head><title>404 Not Found</title></head>
      <body>
      <center><h1>404 Not Found</h1></center>
      <hr><center>nginx/1.18.0 (Ubuntu)</center>
      </body>
      </html>
      ```
   - game

      - create a new game: `http --auth test:test123 POST http://127.0.0.1:5100/newgame`

      Sample Output:
      ```
      'http --auth yourusername:yourpassword POST http://127.0.0.1:5100/newgame'
      {
         "answerid": 3912,
         "gameid": "b0039f36-6784-11ed-ba4a-615e339a8400",
         "username": "yourusername"
      }
      ```
      Note - this will return a `gameid`
    - add a guess: `http --auth yourusername:yourpassword PUT http://127.0.0.1:5100/addguess gameid="gameid" word="yourguess"`

    Sample Output:
    ```
      http --auth yourusername:yourpassword PUT http://127.0.0.1:5100//addguess gameid="b0039f36-6784-11ed-ba4a-615e339a8400" word="amigo"
     {
        "Accuracy": "XXOOO",
        "guessedWord": "amigo"
     }
     ```
    - display your active games: `http --auth yourusername:yourpassword GET http://127.0.0.1:5100/allgames`

    Sample Output:
    ```
      http --auth yourusername:yourpassword GET http://127.0.0.1:5100/allgames
      [
         {
            "gameid": "b0039f36-6784-11ed-ba4a-615e339a8400",
            "gstate": "In-progress",
            "guesses": 1
         }
      ]
      ```
    - display the game status and stats for one game: `http --auth yourusername:yourpassword GET http://127.0.0.1:5100/onegame?id=gameid`
       - example: `.../onegame?id=b97fcbb0-6717-11ed-8689-e9ba279d21b6`
    Sample Output:
    ```
      http --auth yourusername:yourpassword GET http://127.0.0.1:5100/onegame?id="b0039f36-6784-11ed-ba4a-615e339a8400"
      [
         {
             "gameid": "b0039f36-6784-11ed-ba4a-615e339a8400",
            "gstate": "In-progress",
            "guesses": 1
          },
          {
             "accuracy": "XXOOO",
             "guessedword": "amigo"
          }
      ]
      ```
7. Test leaderboard using http docs: http//127.0.0.1:5400/docs

    POST/results
    Sample input:
    ```
        {
        "guesses": 5,
        "result": "win",
        "username": "User"
        }
    ```
    Sample output:
    ```
    {
        "average_score": "2",
        "game_count": "1",
        "result": "win",
        "score": "2",
        "username": "User"
    }
    ```

    GET/leaderboard
    Sample output:
    ```
    curl -X 'GET' \
      'http://127.0.0.1:5400/LeaderBoard/' \
      -H 'accept: */*'
    ```
    ```
    ('userg', 6.0)
    ('usera', 6.0)
    ('userf', 5.0)
    ('userc', 5.0)
    ('userh', 4.0)
    ('usere', 4.0)
    ('userd', 4.0)
    ('userb', 4.0)
    ('user3', 3.0)
    ('user', 3.0)
    ```

 
