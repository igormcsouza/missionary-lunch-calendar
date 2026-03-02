# Missionary Lunch Calendar

[![Pylint](https://github.com/igormcsouza/missionary-lunch-calendar/actions/workflows/pylint.yml/badge.svg)](https://github.com/igormcsouza/missionary-lunch-calendar/actions/workflows/pylint.yml)

This application aims to solve an issue of creating a calendar to the members of the Church of Jesus Christ of Latter Days Saints to give launch to the missionaries. It stores the proposed days the members are available and easily update for next month keeping the days.

## Next steps...

I'm happy to keep updating this project and adding more features, if anyone is interested in giving advice just open the issue and I'm going to analyse and implement if it is necessary!

## How to start the development server

In order to be able to run it locally for development one needs to first install [nodemon](https://www.npmjs.com/package/nodemon) to enable `hot reload` and then run the following command in your terminal on the root of the repositoy...

```bash
nodemon --ext py --exec "python3 app.py --dev --host localhost"
```

Make sure to use `--dev` to let the application know that no firestore connection is necessary... And add `--host` to allow firebase to authenticate correctly.

The application will start and restart every time there is a change to the `.py` file. If there are changes to the `.html` file it the UI will catch it.

There is also a Dockerfile so that people can use all the features from firebase.
