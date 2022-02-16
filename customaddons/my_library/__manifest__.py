{
    'name': 'My Library',
    'version': '1.3',
    'sequence': 10,
    'description': """ """,
    'category': 'Library',
    'license': 'LGPL-3',
    'depends': ['sale', 'contacts', 'base_setup'],
    'data': [
        'data/data.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/security_rules.xml',
        'views/library_book.xml',
        'views/inherit_partner.xml',
        'views/books_copy.xml',
        'views/book_category.xml',
        'views/library_book_rent.xml',
        'views/library_rent_wizard.xml',
        'views/library_return_wizard.xml',
        'views/res_config_settings.xml',
        'views/templates.xml'
    ],
    'post_init_hook': 'add_book_hook',
    'demo': [
        'data/demo.xml'
    ],
    'qweb': [],
    'installable': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
