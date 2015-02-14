require 'RMagick'
include Magick
require 'rqrcode_png'

def MakeQRImage(id, qrSize)
  url = "qr.hal9k.dk/HQR#{id}"
  qr = RQRCode::QRCode.new(url, :size => 4, :level => :h)
  png = qr.to_img.resize(qrSize, qrSize)
  png.save('temp.png')
  return Magick::Image.read('temp.png').first
end

rows = 10
cols = 8
qrSize = 200
xMargin = 20
yMargin = xMargin*2

nofCodes = rows*cols

largeImage = Magick::Image.new(cols*(qrSize+xMargin), rows*(qrSize+yMargin)) {
  self.background_color = 'white'
}

draw = Magick::Draw.new

id = 1000
for row in 1..rows
  for col in 1..cols
    if true
      img = MakeQRImage(id, qrSize)
      largeImage.composite!(img, (col-1)*(qrSize+xMargin), (row-1)*(qrSize+yMargin), AtopCompositeOp)
    end
    if true
      draw.annotate(largeImage, qrSize, yMargin, (col-1)*(qrSize+xMargin), (row-1)*(qrSize+yMargin)+qrSize-10, "HQR#{id}") do
        self.font = 'Helvetica'
        self.pointsize = 40
        #self.font_weight = Magick::BoldWeight
        self.fill = 'black'
        self.gravity = Magick::CenterGravity
      end
    end
    id = id + 1
  end
end

largeImage.write('qr.png')
