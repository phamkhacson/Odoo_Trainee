from odoo import fields, models, api, tools


class LibraryBookRent(models.Model):
    _name = 'library.book.rent'
    book_id = fields.Many2one('library.book', 'Book', required=True)
    borrower_id = fields.Many2one('res.partner', 'Borrower', required=True)
    state = fields.Selection([
        ('ongoing', 'Ongoing'),
        ('returned', 'Returned'),
        ('lost', 'Lost')],
        'State', default='ongoing', required=True)
    rent_date = fields.Date(default=fields.Date.today)
    return_date = fields.Date()

    def book_lost(self):
        self.ensure_one()
        self.book_id.make_lost()
        self.sudo().state = 'lost'
        book_with_different_context = self.book_id.with_context(avoid_deactivate=True)
        book_with_different_context.sudo().make_lost()

    def book_return(self):
        self.ensure_one()
        self.book_id.make_available()
        self.write({
            'state': 'returned',
            'return_date': fields.date.today()
        })


class LibraryBookRentStatistics(models.Model):
    _name = 'library.book.rent.statistics'
    _auto = False
    book_id = fields.Many2one('library.book',
                              string='Book',
                              readonly=True)
    rent_count = fields.Integer(string="Times borrowed",
                                readonly=True)
    average_occupation = fields.Integer(string="Average Occupation (DAYS)",
                                        readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
             CREATE OR REPLACE VIEW library_book_rent_statistics AS (
             SELECT
             min(lbr.id) as id,
             lbr.book_id as book_id,
             count(lbr.id) as rent_count,
             avg((EXTRACT(epoch from age(return_date, rent_date)) / 86400))::int as average_occupation
             FROM
             library_book_rent AS lbr
             JOIN
             library_book as lb ON lb.id = lbr.book_id
             WHERE lbr.state = 'returned'
             GROUP BY lbr.book_id
             );
             """
        self.env.cr.execute(query)
