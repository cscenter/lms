-- Run dev environment: osascript launch.scpt
on run argv
  tell application "iTerm"
    set defaults to {"8000"}
    set opts to {port:item 1 of (argv & defaults)}

    tell current session of current window
      write text "./manage.py runserver " & opts's port
    end tell

    tell current window
      create tab with default profile
      tell current session of current tab
        write text "npm run gulp -- --port " & opts's port
      end tell

      create tab with default profile
      tell current session of current tab
        write text "npm start"
      end tell
    end tell
  end tell
end run