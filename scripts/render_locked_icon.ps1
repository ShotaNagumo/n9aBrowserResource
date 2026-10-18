# Independent geometric lock icon. No third-party image or icon paths are used.
# Geometry matches icons/equipment/Locked.svg; output is transparent PNG at 256px.
Add-Type -AssemblyName System.Drawing
$repo=Split-Path $PSScriptRoot -Parent
$bitmap=New-Object Drawing.Bitmap(256,256)
$graphics=[Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([Drawing.Color]::Transparent)
$graphics.ScaleTransform(4,4)
$light=[Drawing.ColorTranslator]::FromHtml('#EAEAEA')
$brush=New-Object Drawing.SolidBrush($light)
$pen=New-Object Drawing.Pen($light,6)
$graphics.DrawLine($pen,20,29,20,19)
$graphics.DrawArc($pen,20,7,24,24,180,180)
$graphics.DrawLine($pen,44,19,44,29)
$body=New-Object Drawing.Drawing2D.GraphicsPath
$body.AddArc(11,26,14,14,180,90)
$body.AddArc(39,26,14,14,270,90)
$body.AddArc(39,44,14,14,0,90)
$body.AddArc(11,44,14,14,90,90)
$body.CloseFigure()
$graphics.FillPath($brush,$body)
$keyBrush=New-Object Drawing.SolidBrush([Drawing.ColorTranslator]::FromHtml('#273241'))
$graphics.FillEllipse($keyBrush,29,38,6,6)
$points=[Drawing.PointF[]]@([Drawing.PointF]::new(31,42),[Drawing.PointF]::new(33,42),[Drawing.PointF]::new(35,49),[Drawing.PointF]::new(29,49))
$graphics.FillPolygon($keyBrush,$points)
$bitmap.Save((Join-Path $repo 'icons/equipment/Locked.png'),[Drawing.Imaging.ImageFormat]::Png)
$keyBrush.Dispose();$body.Dispose();$pen.Dispose();$brush.Dispose();$graphics.Dispose();$bitmap.Dispose()
