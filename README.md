# Missionary Launch Calendar

This application aims to solve an issue of creating a calendar to the members of the Church of Jesus Christ of Latter Days Saints to give launch to the missionaries. It stores the proposed days the members are available and easily update for next month keeping the days.

## TODO
- [X] Remove the week 6 from the calendar picture if there is no date to there
- [X] Update the text to present its meaning better, and traslate to portuguese in the picture
- [X] Add the ability to add more names to each box, the idea is that people can occupy more than one place in the day
- [ ] Create a dockerfile to run the application from it, so I can easily ship this to production
- [X] Create a hot reload feature for development process
- [X] Update theme to be Dark Mode
- [ ] Add a more roboust storage data like dbm

## How to start the development server

In order to be able to run it locally for development one needs to first install [nodemon](https://www.npmjs.com/package/nodemon) to enable `hot reload` and then run the following command in your terminal on the root of the repositoy...

```bash
nodemon --ext py --exec "python3 app.py"
```

The application will start and restart everytime there is a change to the `.py` file. If somebody change the `.html` file it automatically update the UI. 
