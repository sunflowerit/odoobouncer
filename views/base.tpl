<!DOCTYPE html>
<html>
  <head>
    % if branding:
    <title>{{ branding }} Login</title>
    % else:
    <title>Login</title>
    % end
    <link type="text/css" href="static/login.css" rel="stylesheet">
    <style>
        html {
          background-color: {{ backgroundcolor }};
        }

        .login form button {
          background: {{ buttoncolor }};
          border-bottom-color: {{ buttonshadowcolor }};
        }

        .login form button:hover {
          background: {{ buttonhovercolor }};
        }
    </style>

  </head>

  <body>
    {{!base}}
  </body>
</html>
