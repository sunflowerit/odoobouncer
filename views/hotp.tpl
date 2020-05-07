<!DOCTYPE html>
<html>
  <head>
    <title>Freshfilter Login</title>
    <link type="text/css" href="static/login.css" rel="stylesheet">
  </head>

  <body>

    <div class="login">
      <div class="heading">
        <h2>Enter six-digit security code, sent to you by email</h2>
        <form method="post">
          <input type="hidden" name="counter" value="{{ counter }}">
          <input type="hidden" name="code" value="{{ code }}">

          <div class="input-group input-group-lg">
            <span class="input-group-addon"><i class="fa fa-key"></i></span>
            <input name="hotp_code" type="text" class="form-control" placeholder="Security code">
          </div>

          <button type="submit" class="float">Login</button>

        </form>
      </div>
    </div>

  </body>
</html>
