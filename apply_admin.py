import re

with open('app.py', 'r') as f:
    content = f.read()

admin_route = """
@app.route('/admin')
def admin_panel():
    # Simple unauthenticated admin panel for v1 demonstration
    # In production, this MUST be secured with login/JWT/Sessions
    mangas = Manga.query.all()
    chapters = Chapter.query.count()

    html = '''
    <html>
    <head><title>Admin Panel</title><style>body{font-family:sans-serif; background:#f4f4f4; padding:20px;} table{width:100%; border-collapse:collapse;} th,td{padding:10px; border:1px solid #ddd; text-align:left;} th{background:#333;color:white;}</style></head>
    <body>
        <h1>Admin Dashboard</h1>
        <p>Total Cached Manga: <b>{{ mangas|length }}</b></p>
        <p>Total Cached Chapters: <b>{{ chapter_count }}</b></p>

        <h2>Cached Manga Database</h2>
        <table>
            <tr><th>ID</th><th>Title</th><th>Last Updated</th><th>Action</th></tr>
            {% for m in mangas %}
            <tr>
                <td>{{ m.id }}</td>
                <td>{{ m.title }}</td>
                <td>{{ m.last_updated }}</td>
                <td>
                    <form action="/admin/delete/{{m.id}}" method="post" style="display:inline;">
                        <button type="submit" style="color:red;">Delete (DMCA)</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, mangas=mangas, chapter_count=chapters)

from flask import render_template_string

@app.route('/admin/delete/<path:manga_id>', methods=['POST'])
def admin_delete(manga_id):
    # DMCA removal feature
    manga = db.session.get(Manga, manga_id)
    if manga:
        Chapter.query.filter_by(manga_id=manga_id).delete()
        db.session.delete(manga)
        db.session.commit()
    return f"<script>alert('Manga {manga_id} and its chapters removed.'); window.location.href='/admin';</script>"
"""

# Insert admin route before main
if '@app.route(\'/admin\')' not in content:
    content = content.replace("if __name__ == '__main__':", admin_route + "\nif __name__ == '__main__':")

with open('app.py', 'w') as f:
    f.write(content)
print("Admin routes added.")
