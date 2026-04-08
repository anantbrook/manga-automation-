import time
from flask import Flask
from models import db, Manga, Chapter

def setup_db():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    app.app_context().push()
    db.create_all()

    # Add a mock manga
    manga_id = 'mock_manga'
    manga = Manga(id=manga_id, title='Mock Manga')
    db.session.add(manga)
    db.session.commit()

    # Add 100 existing chapters
    for i in range(100):
        chapter = Chapter(id=f'{manga_id}/chap-{i}', manga_id=manga_id, title=f'Chapter {i}', url='http://example.com')
        db.session.add(chapter)
    db.session.commit()

    return manga_id

def original_n1_approach(manga_id, details):
    start = time.time()
    new_chapters = []
    for chap in details['chapters']:
        existing = db.session.get(Chapter, chap['id'])
        if not existing:
            chapter = Chapter(id=chap['id'], manga_id=manga_id, title=chap['title'], url=chap['url'])
            db.session.add(chapter)
            new_chapters.append(chap)
    db.session.commit()
    end = time.time()
    return end - start, new_chapters

def optimized_approach(manga_id, details):
    start = time.time()
    new_chapters = []
    # Fetch all existing chapter IDs into a set
    existing_chapter_ids = {c[0] for c in db.session.query(Chapter.id).filter_by(manga_id=manga_id).all()}

    for chap in details['chapters']:
        if chap['id'] not in existing_chapter_ids:
            chapter = Chapter(id=chap['id'], manga_id=manga_id, title=chap['title'], url=chap['url'])
            db.session.add(chapter)
            new_chapters.append(chap)
    db.session.commit()
    end = time.time()
    return end - start, new_chapters

def main():
    manga_id = setup_db()

    # Details has 150 chapters: 100 existing, 50 new
    details = {
        'chapters': [
            {'id': f'{manga_id}/chap-{i}', 'title': f'Chapter {i}', 'url': 'http://example.com'}
            for i in range(150)
        ]
    }

    # Since they both add the 50 new chapters, we need to run them on clean databases
    db.drop_all()

    manga_id = setup_db()
    time_n1, new_n1 = original_n1_approach(manga_id, details)

    db.drop_all()

    manga_id = setup_db()
    time_opt, new_opt = optimized_approach(manga_id, details)

    print(f"Original N+1 Time: {time_n1:.6f} seconds")
    print(f"Optimized Time:    {time_opt:.6f} seconds")
    print(f"Improvement:       {time_n1 / time_opt:.2f}x faster")
    assert len(new_n1) == 50
    assert len(new_opt) == 50

if __name__ == '__main__':
    main()
