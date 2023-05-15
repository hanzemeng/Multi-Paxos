import blogapp

if __name__ == '__main__':
    bethesda_game_forum = blogapp.Forum()

    b1 = blogapp.Blog('crdgdr', 'Morrowind is the BEST', 'title^')
    c1 = blogapp.Comment('crdgdr', 'Morrowind is the BEST', 'so ture!')
    b2 = blogapp.Blog('crdgdr', 'When will we get Starfield?', "It's taking forever")
    b3 = blogapp.Blog('crdgdr', 'Morrowind is the BEST', 'Yet another Morrowind post')

    print('Empty forum:')
    bethesda_game_forum.print_all()
    bethesda_game_forum.view_user('crdgdr')
    bethesda_game_forum.read_title('?')
    bethesda_game_forum.post_comment(c1, '?')
    print()

    bethesda_game_forum.post_blog(b1)
    bethesda_game_forum.post_comment(c1, 'Morrowind is the BEST')

    print('One post:')
    print('Print all:')
    bethesda_game_forum.print_all()
    print('View user:')
    bethesda_game_forum.view_user('crdgdr')
    print('Read title:')
    bethesda_game_forum.read_title('Morrowind is the BEST')

    print('Duplicate title:')
    bethesda_game_forum.post_blog(b3)
    print()

    bethesda_game_forum.post_blog(b2)
    print('Two posts:')
    print('Print all:')
    bethesda_game_forum.print_all()
    print('View user:')
    bethesda_game_forum.view_user('crdgdr')
    print('Read title:')
    bethesda_game_forum.read_title('When will we get Starfield?')
