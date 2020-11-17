import math

class Grid(object):

    def __init__(self, completed_bit_vector):
        self.rows, self.cols = self.dim(len(completed_bit_vector))
        self.status = [ completed_bit_vector[j*self.cols:(j+1)*self.cols] for j in range(self.rows) ]
        self.borders()

    def borders(self):
        allbox = u''.join(chr(9472 + x) for x in range(200))
        box = [ allbox[i] for i in (78, 0, 12, 16, 20, 24) ]
        (self.vbar, hbar, ul, ur, ll, lr) = box
        h3 = hbar * 4
        self.topline = ul + h3 * (self.cols - 1)  + ur
        # self.midline = self.vbar + ('   ') * (self.cols - 1) + self.vbar
        self.botline = ll + h3 * (self.cols - 1) + lr


    def display_grid(self):
        print(self.topline)
        for i in range(self.rows - 1):
            row_status = ''.join([ '  ' if block == 0 else chr(9472 + 141) for piece in self.status for block in piece ])
            print(self.vbar + row_status + self.vbar)
            # print(self.midline)
        print(self.botline)


    def dim(self, num_pieces):
        factor_pairs = self.pairs(num_pieces)
        return min(factor_pairs, key=lambda x: abs(x[0]-x[1]))

    def pairs(self, num):
        return [ (i, num//i) for i in range(1, int(math.sqrt(num))+1) if num % i == 0 ]

    


grid = Grid([ 1 for _ in range(525)])
grid.display_grid()
