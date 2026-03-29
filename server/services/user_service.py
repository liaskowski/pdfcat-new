import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from ..models import User

def delete_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    # Delete physical files
    # We need to iterate over a copy or list because accessing relationships during delete might be tricky?
    # Actually, getting the list first is safe.
    documents = user.documents
    for doc in documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                print(f"Error deleting file {doc.file_path}: {e}")

    # Delete avatar
    if user.avatar_url:
        # avatar_url is relative: "static/avatars/user_1.jpg"
        # We need to prepend server root or just use it if it is relative to cwd (server running from root)
        # Based on users.py: avatar_dir = "server/static/avatars"
        # And saved as relative_url = f"static/avatars/{filename}"
        # So we need to prefix "server/" if running from root?
        # users.py says: avatar_dir = "server/static/avatars", relative_url = "static/avatars/..."
        # So path = "server/" + user.avatar_url ?
        # user.avatar_url starts with "static/".
        # Let's try to construct path.
        
        possible_path = os.path.join("server", user.avatar_url)
        if os.path.exists(possible_path):
            try:
                os.remove(possible_path)
            except Exception as e:
                print(f"Error deleting avatar {possible_path}: {e}")
        else:
             # Try without 'server' prefix just in case
            if os.path.exists(user.avatar_url):
                 try:
                    os.remove(user.avatar_url)
                 except Exception as e:
                    print(f"Error deleting avatar {user.avatar_url}: {e}")

    db.delete(user)
    db.commit()
    return {"message": f"User {user.username} deleted successfully"}
