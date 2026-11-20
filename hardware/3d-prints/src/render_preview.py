import sys,trimesh,numpy as np,matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
names=sys.argv[2:]; fig=plt.figure(figsize=(4*len(names),4))
for i,n in enumerate(names):
    m=trimesh.load(f'{sys.argv[1]}/{n}.stl'); ax=fig.add_subplot(1,len(names),i+1,projection='3d')
    tri=m.vertices[m.faces]; nrm=m.face_normals; shade=0.35+0.65*np.clip(nrm@np.array([0.4,-0.5,0.77]),0,1)
    pc=Poly3DCollection(tri,facecolors=plt.cm.Blues(0.3+0.6*shade),edgecolor='none'); ax.add_collection3d(pc)
    mn,mx=m.bounds; c=(mn+mx)/2; r=(mx-mn).max()/2
    ax.set_xlim(c[0]-r,c[0]+r); ax.set_ylim(c[1]-r,c[1]+r); ax.set_zlim(c[2]-r,c[2]+r); ax.set_title(n,fontsize=9); ax.view_init(28,-60); ax.set_axis_off()
plt.tight_layout(); plt.savefig(sys.argv[1]+'/../preview_'+names[0]+'.png',dpi=90)
