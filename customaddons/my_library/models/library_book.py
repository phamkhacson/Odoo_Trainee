from odoo import fields, models, api
from odoo.exceptions import ValidationError, UserError, _logger
from datetime import timedelta
from odoo.tests.common import Form


class LibraryMember(models.Model):
    _name = 'library.member'
    _inherits = {'res.partner': 'partner_id'}
    partner_id = fields.Many2one(
        'res.partner',
        ondelete='cascade')
    date_start = fields.Date('Member Since')
    date_end = fields.Date('Termination Date')
    member_number = fields.Char()
    date_of_birth = fields.Date('Date of birth')


class BaseArchive(models.AbstractModel):
    _name = 'base.archive'
    active = fields.Boolean(default=True)

    def do_archive(self):
        for record in self:
            record.active = not record.active


class LibraryBook(models.Model):
    _name = 'library.book'
    _inherit = ['base.archive']
    _description = 'Library Book'
    _order = 'date_release desc, name'
    _rec_name = 'short_name'
    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)',
         'Book title must be unique.'),
        ('positive_page', 'CHECK(pages>0)',
         'No of pages must be positive')
    ]
    name = fields.Char('Title', required=True)
    short_name = fields.Char('Short Title', required=True)
    notes = fields.Text('Internal Notes')
    category_id = fields.Many2one('library.book.category')
    old_edition = fields.Many2one('library.book', string='Old Edition')
    author_ids = fields.Many2many('res.partner', string='Authors')
    state = fields.Selection(
        [('draft', 'Unavailable'),
         ('available', 'Available'),
         ('borrowed', 'Borrowed'),
         ('lost', 'Lost')],
        'State', default="draft")
    description = fields.Html('Description')
    manager_remarks = fields.Text('Manager Remarks')
    cover = fields.Binary('Book Cover')
    out_of_print = fields.Boolean('Out of Print?')
    date_release = fields.Date('Release Date', groups='my_library.group_release_dates')
    date_updated = fields.Datetime('Last Updated')
    date_return = fields.Date('Date to return')
    pages = fields.Integer('Number of Pages')
    reader_rating = fields.Float('Reader Average Rating', digits=(14, 4))
    cost_price = fields.Float('Book Cost', digits='Book Price')
    currency_id = fields.Many2one('res.currency', string='Currency')
    retail_price = fields.Monetary('Retail Price', )
    publisher_id = fields.Many2one(
        'res.partner', string='Publisher',
        ondelete='set null',
        context={},
        domain=[],
    )
    publisher_city = fields.Char(
        'Publisher City',
        related='publisher_id.city',
        readonly=True)
    age_days = fields.Float(
        string='Days Since Release',
        compute='_compute_age',
        inverse='_inverse_age',
        search='_search_age',
        store=False,
        compute_sudo=True
    )
    ref_doc_id = fields.Reference(
        selection='_referencable_models',
        string='Reference Document')
    is_public = fields.Boolean(groups='my_library.group_librarian')
    private_notes = fields.Text(groups='my_library.group_librarian')
    report_missing = fields.Text(
        string="Book is missing",
        groups='my_library.group_librarian')
    activity_ids = fields.Boolean()

    def name_get(self):
        result = []
        for book in self:
            authors = book.author_ids.mapped('name')
            name = '%s (%s)' % (book.name, ', '.join(authors))
            result.append((book.id, name))
        return result

        # check date release

    @api.constrains('date_release')
    def _check_release_date(self):
        for record in self:
            if record.date_release and record.date_release > fields.Date.today():
                raise models.ValidationError('Release date must be in the past')

    # calculator age days
    @api.depends('date_release')
    def _compute_age(self):
        today = fields.Date.today()
        for book in self:
            if book.date_release:
                delta = today - book.date_release
                book.age_days = delta.days
            else:
                book.age_days = 0

    def _inverse_age(self):
        today = fields.Date.today()
        for book in self.filtered('date_release'):
            d = today - timedelta(days=book.age_days)
            book.date_release = d

    def _search_age(self, operator, value):
        today = fields.Date.today()
        value_days = timedelta(days=value)
        value_date = today - value_days
        operator_map = {
            '>': '<', '>=': '<=',
            '<': '>', '<=': '>=',
        }
        new_op = operator_map.get(operator, operator)
        return [('date_release', new_op, value_date)]

    # Reference Document
    @api.model
    def _referencable_models(self):
        models = self.env['ir.model'].search([('field_id.name', '=', 'message_ids')])
        return [(x.model, x.name) for x in models]

    @api.model
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'available'),
                   ('available', 'borrowed'),
                   ('borrowed', 'available'),
                   ('available', 'lost'),
                   ('borrowed', 'lost'),
                   ('lost', 'available')]
        return (old_state, new_state) in allowed

    def change_state(self, new_state):
        for book in self:
            if book.is_allowed_transition(book.state, new_state):
                book.state = new_state
            else:
                msg = ('Moving from %s to %s is not allowed') % (book.state, new_state)
                raise UserError(msg)

    def make_available(self):
        self.change_state('available')
        self.date_return = False

    def make_borrowed(self):
        self.change_state('borrowed')
        day_to_borrow = self.category_id.max_borrow_days or 10
        self.date_return = fields.Date.today() + timedelta(days=day_to_borrow)

    def make_lost(self):
        self.ensure_one()
        self.state = 'lost'

    def make_unavailable(self):
        self.change_state('draft')

    def log_all_library_members(self):
        library_member_model = self.env['library.member']
        all_members = library_member_model.search([])
        print("ALL MEMBERS:", all_members)
        return True

    def change_release_date(self):
        self.ensure_one()
        self.date_release = fields.Date.today()

    def find_book(self):
        domain = ['|', '&', ('name', 'ilike', 'Book Name'), ('category_id.name', 'ilike', 'CategoryName'), '&',
                  ('name', 'ilike', 'Book Name 2'), ('category_id.name', 'ilike', 'Category Name2')]
        books = self.search(domain)

    def find_partner(self):
        PartnerObj = self.env['res.partner']
        domain = [
            '&', ('name', 'ilike', 'Parth Gajjar'),
            ('company_id.name', '=', 'Odoo')
        ]
        partner = PartnerObj.search(domain)

    @api.model
    def books_with_multiple_authors(self, all_books):
        def predicate(book):
            if len(book.author_ids) > 1:
                return True
            return False

        return all_books.filter(predicate)

    @api.model
    def get_author_names(self, books):
        return books.mapped('author_ids.name')

    @api.model
    def sort_books_by_date(self, books):
        return books.sorted(key='release_date')

    @api.model
    def create(self, values):
        if not self.user_has_groups('my_library.group_librarian'):
            if 'manager_remarks' in values:
                raise UserError(
                    'You are not allowed to modify '
                    'manager_remarks'
                )
        return super(LibraryBook, self).create(values)

    def write(self, values):
        if not self.user_has_groups('my_library.group_librarian'):
            if 'manager_remarks' in values:
                raise UserError(
                    'You are not allowed to modify '
                    'manager_remarks'
                )
        return super(LibraryBook, self).write(values)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = [] if args is None else args.copy()
        if not (name == '' and operator == 'ilike'):
            args += ['|', '|', ('name', operator, name),
                     ('isbn', operator, name),
                     ('author_ids.name', operator, name)]
        return super(LibraryBook, self)._name_search(
            name=name, args=args, operator=operator,
            limit=limit, name_get_uid=name_get_uid)

    @api.model
    def _get_average_cost(self):
        grouped_result = self.read_group(
            [('cost_price', "!=", False)],
            ['category_id', 'cost_price:avg'],
            ['category_id'])
        return grouped_result

    def book_rent(self):
        self.ensure_one()
        if self.state != 'available':
            raise UserError('Book is not available for renting')
        rent_as_superuser = self.env['library.book.rent'].sudo()
        rent_as_superuser.create({
            'book_id': self.id,
            'borrower_id': self.env.user.partner_id.id,
        })
        self.make_borrowed()

    def average_book_occupation(self):
        self.flush()
        sql_query = """
             SELECT
             lb.name, avg((EXTRACT(epoch from age(return_date, rent_date)) / 86400))::int
             FROM
             library_book_rent AS lbr
             JOIN
             library_book as lb ON lb.id = lbr.book_id
             WHERE lbr.state = 'returned'
             GROUP BY lb.name;"""
        self.env.cr.execute(sql_query)
        result = self.env.cr.fetchall()
        _logger.info("Average book occupation: %s", result)
        print(result)

    def return_all_books(self):
        self.ensure_one()
        wizard = self.env['library.return.wizard']
        with Form(wizard) as return_form:
            return_form.borrower_id = self.env.user.partner_id
            record = return_form.save()
            record.books_returns()

    def report_missing_book(self):
        self.ensure_one()
        message = "Book is missing (Reported by: %s)" % self.env.user.name
        self.sudo().write({
            'report_missing': message
        })
