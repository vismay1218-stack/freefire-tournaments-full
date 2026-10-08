def register_cli(app):
    from app.cli.admin_cmd import register_admin_cmd
    register_admin_cmd(app)
