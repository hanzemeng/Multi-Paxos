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

    def format_title(self) -> str:
        return f'{self.title}'
    
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
    
    def post_blog(self, b: Blog):
        for existing in self.blogs:
            if existing.title == b.title:
                print('DUPLICATE TITLE', flush=True)
                return
        self.blogs.append(b)
    
    def post_comment(self, c: Comment, t: str):
        for b in self.blogs:
            if b.title == t:
                b.add_comment(c)
                return
        print('CANNOT COMMENT', flush=True)
    
    def print_all(self):
        if not self.blogs:
            print('BLOG EMPTY', flush=True)
            return
        print('\n'.join(map(Blog.format_title, self.blogs)) + '\n', flush=True)
    
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
