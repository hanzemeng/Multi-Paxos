class Comment:
    def __init__(self, username: str, title: str, content: str):
        self.username = username
        self.title = title
        self.content = content
    
    def format_comment(self) -> str:
        return f' {self.username}: {self.content}'

class Blog:
    def __init__(self, username: str, title: str, content: str):
        self.username = username
        self.title = title
        self.content = content
        self.comments = []
    
    def add_comment(self, c: Comment):
        c.title = self.title
        self.comments.append(c)
    
    def format_title_content(self) -> str:
        return f'Title: {self.title}\nContent: {self.content}\n'

    def format_full(self) -> str:
        c = '\n'.join(map(Comment.format_comment, self.comments))
        if not c:
            return f'Title: {self.title}\nUsername: {self.username}\nContent: {self.content}\nComments: ~~Add your comment~~\n'
        return f'Title: {self.title}\nUsername: {self.username}\nContent: {self.content}\nComments:\n{c}\n'

class Forum:
    def __init__(self):
        self.blogs = []
    
    def post_blog(self, b: Blog) -> bool:
        for existing in self.blogs:
            if existing.title == b.title:
                print('DUPLICATE TITLE', flush=True)
                return False
        self.blogs.append(b)
        print(f'NEW POST *{b.title}* from user *{b.username}*', flush=True)
        return True
    
    def post_comment(self, c: Comment) -> bool:
        for b in self.blogs:
            if b.title == c.title:
                b.add_comment(c)
                print(f'NEW COMMENT on *{c.title}* from user *{c.username}*', flush=True)
                return True
        print('CANNOT COMMENT', flush=True)
        return False
    
    def print_all(self):
        if not self.blogs:
            print('BLOG EMPTY', flush=True)
            return
        print('\n'.join(b.title for b in self.blogs) + '\n', flush=True)
    
    def view_user(self, u: str):
        user_blogs = []
        for b in self.blogs:
            if b.username == u:
                user_blogs.append(b)
        if not user_blogs:
            print('NO POST', flush=True)
            return
        print('\n'.join(map(Blog.format_title_content, user_blogs)), flush=True)
    
    def read_title(self, t: str):
        for b in self.blogs:
            if b.title == t:
                print(b.format_full(), flush=True)
                return
        print('POST NOT FOUND', flush=True)
