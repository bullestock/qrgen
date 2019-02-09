require 'rmagick'
include Magick
require 'rqrcode_png'

def MakeQRImage(id, qrSize)
  url = "http://qr.hal9k.dk/HQR#{id}"
  qr = RQRCode::QRCode.new(url, :size => 4, :level => :h)
  png = qr.to_img.resize(qrSize, qrSize).crop(20, 20, 340, 340)
  png.save('temp.png')
  return Magick::Image.read('temp.png').first
end

# top/bottom 25, left/right 7
# image width 185 mm

rows = 5
cols = 4
xMargin = 120
yMargin = 120

qrSize = 380
imgSize = 380 - 40
fontSize = 40

nofCodes = rows*cols

largeImage = Magick::Image.new(cols*(imgSize+xMargin) - xMargin, rows*(imgSize+yMargin) + 2*yMargin) {
  self.background_color = 'white'
}

draw = Magick::Draw.new

id = 110
for row in 1..rows
  for col in 1..cols
    if true
      img = MakeQRImage(id, qrSize)
      largeImage.composite!(img, (col-1)*(imgSize+xMargin), (row-1)*(imgSize+yMargin) + yMargin, AtopCompositeOp)
    end
    if true
      draw.annotate(largeImage, imgSize, yMargin, (col-1)*(imgSize+xMargin), (row-1)*(imgSize+yMargin)+yMargin+imgSize, "HQR#{id}") do
        self.font = 'Helvetica'
        self.pointsize = fontSize
        #self.font_weight = Magick::BoldWeight
        self.fill = 'black'
        self.gravity = Magick::CenterGravity
      end
    end
    id = id + 1
  end
end

largeImage.write('qr-45.png')
