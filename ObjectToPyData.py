import bpy, bmesh, re

# Get the active mesh
me = bpy.context.object.data

mefilename2 = re.sub(r'[^\w\s]', '', str(me.name))+".py"
mefilename = re.sub(r'[0-9]', '', mefilename2)
print(mefilename)

file = open(mefilename, 'w', encoding="utf-8")

# Get a BMesh representation
bm = bmesh.new()   # create an empty BMesh
bm.from_mesh(me)   # fill it in from a Mesh

print("\n\n\n")

z="["

numc = len(bm.faces)-1
for f in bm.faces:
    z+="["
    numcc = len(f.verts)-1
    for v in f.verts:
        z+=str(v.index)
        if numcc>0:
            z+=","
        numcc-=1
    if numc>0:
        z+="],"
    numc-=1
z+="]]"

vert="[\n"
for v in bm.verts:
    vert+="Vector((" +str(v.co.x)+","+str(v.co.y)+","+str(v.co.z)+")),\n"
vert+="]"

zz="["

numcz = len(bm.edges)-1
for e in bm.edges:
    zz+="["
    numccz = len(e.verts)-1
    for v in e.verts:
        zz+=str(v.index)
        if numccz>0:
            zz+=","
        numccz-=1
    if numcz>0:
        zz+="],"
    numcz-=1
zz+="]]"

text="verts = "
text+=vert
text+="\n\nedges = "
text+=zz
text+="\n\nfaces = "
text+=z
text+="\n\n"

#print(text)

file.write(text)