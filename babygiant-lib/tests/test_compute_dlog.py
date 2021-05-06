import unittest

import babygiant


def to_le_32_hex_bytes(num):
    hx = "{0:0{1}x}".format(num, 32*2)
    b = "".join(reversed(["".join(x) for x in zip(*[iter(hx)] * 2)]))
    return b


class TestComputeDlog(unittest.TestCase):

    def test_compute_dlog1(self):
        x = 11904062828411472290643689191857696496057424932476499415469791423656658550213
        y = 9356450144216313082194365820021861619676443907964402770398322487858544118183
        self.assertEqual("1", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog2(self):
        x = 141579968252753561777903806704988380915591798817413028638954837858390837201
        y = 8211442360329077616485844356105856211290554633036363698328149195845491718472
        self.assertEqual("42", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog3(self):
        x = 1237782632357792921748619918672290873715140228147952285260614658227666644805
        y = 8536601915096873801487482824890195798313989719405833310308025351040807340450
        self.assertEqual("439864", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog4(self):
        x = 5652656239952688394277263857437950310337758360686799204608403639751231094469
        y = 12851660065128060156182676833734308532414060198909711906752076757704989086093
        self.assertEqual("29479828", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog5(self):
        x = 15743946954562047249571095208238595903506448530691319295399660626995714375664
        y = 15525990578248253221389285433096584355731520235111340770355552827779786069736
        self.assertEqual("20503", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog6(self):
        x = 938459532454339079955561771272595017136409256765296385851682915539698976422
        y = 3427543513549742811527812325486389539662919266205813455803260249255161169399
        self.assertEqual("9973", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))

    def test_compute_dlog7(self):
        x = 19121738117514367125825473914004741810707492687275644297534200073386934052875
        y = 8407169098186914336744034121476531686413014126989797732313769594461994647750
        self.assertEqual("11", babygiant.compute_dlog(to_le_32_hex_bytes(x), to_le_32_hex_bytes(y)))
