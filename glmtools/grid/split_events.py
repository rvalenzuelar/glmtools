import numpy as np
import xarray as xr

# from concurrent.futures import ProcessPoolExecutor
# pool = ProcessPoolExecutor()
from functools import partial

import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

double_array = partial(np.asarray, dtype='f8')
def gen_sq_mean(sq):
    sqa = double_array(sq)
    sqm = np.einsum(sqa, [0,Ellipsis], [Ellipsis]) / float(sqa.shape[0])
    return sqa, sqm

def gen_split_events(chopped_polys, poly_areas, slicer, event_ids=None):
    """
    chopped_polys is a list of N polygons whose elements contain the sub-polys of each polygon.
        It is the data structure created by QuadMeshPolySlicer.slice
    event_ids are N corresponding event_ids
    """
    if event_ids is None: 
        log.debug("Faking event ids")
        event_ids = range(len(chopped_polys))
    

    for (subquads, frac_areas, (x_idxs, y_idxs)), total_area, evid in zip(chopped_polys, poly_areas, event_ids):
        quad_fracs = slicer.quad_frac_from_poly_frac_area(
                        frac_areas, total_area, x_idxs, y_idxs)
        # While this runs faster without the call to tuple,
        # the chained map iterators result in a swiss cheese grid
        # because the mean consumes an array, leaving it unavailable for
        # the zip loop below.
        # sq_arrays = tuple(map(double_array, subquads))
        # About 70% of the runtime of this function is in calculating the
        # mean positions.
        # sq_means = tuple(map(mean_ax0, sq_arrays))
        sq_means = map(gen_sq_mean, subquads)

        for (sq, sq_mean), frac_area, x_idx, y_idx, quad_area in zip(
                sq_means, frac_areas, x_idxs, y_idxs, quad_fracs):
            yield(sq, sq_mean, frac_area, quad_area, (x_idx, y_idx), evid)

def split_event_data(split_polys, poly_areas, slicer, event_ids):
    """
    split_polys is a list of N original polygons whose elements contain the
    sub-polys of each polygon. It is the data structure created by 
    QuadMeshPolySlicer.slice

    event_ids are N corresponding event_ids
    """

    # fromiter would run faster if we could precalculate the count, though
    # doing so would require iterating to sum some sizes, so it's not clear
    # if there's much net benefit.
    dtype = np.dtype([
#         ('poly','f8',(4,2)), # polys could be any number of verts, so don't use.
        ('poly_ctr', 'f8', (2,)),
        ('event_frac_area', 'f8'),
        ('mesh_frac_area', 'f8'),
        ('mesh_idx', 'i8', (2,)),
#         ('mesh_y_idx', 'i8'),
        ('event_id', 'u8')
    ])
    
    parts_of_split_polys = [p for p in 
        gen_split_events(split_polys, poly_areas, slicer, event_ids=event_ids)]
    
    # Each element here will be an (n_verts, 2) array of polygon vertex locations.
    sub_polys = [sp[0] for sp in parts_of_split_polys]

    # These are frac_area, quad_area, (x_idx, y_idx), evid - i.e., 
    # the parts with the same length that can be turned into an array.
    split_event_property_iter = (sp[1:] for sp in parts_of_split_polys)
    
    n_sub_polys = len(sub_polys)
    
#     for sp, (frac_area, quad_area, idxs, evid) in zip(sub_polys, split_event_property_iter):
#         sp.mean(axis=0)
    
    d = np.fromiter(split_event_property_iter, dtype=dtype, count=n_sub_polys)

    return sub_polys, d

def split_event_dataset_from_props(props, centroid_names=('split_event_lon',
                                                          'split_event_lat')):
    """ props is the numpy array with named dtype returned by split_event_dataset """
    
    dims = ('number_of_split_event_children',)
    d ={
        centroid_names[0]: {'dims':dims, 'data':props['poly_ctr'][:,0]},
        centroid_names[1]: {'dims':dims, 'data':props['poly_ctr'][:,1]},
        'split_event_mesh_area_fraction': {'dims':dims, 'data':props['mesh_frac_area']},
        'split_event_area_fraction': {'dims':dims, 'data':props['event_frac_area']},
        'split_event_mesh_x_idx': {'dims':dims, 'data':props['mesh_idx'][:,0]},
        'split_event_mesh_y_idx': {'dims':dims, 'data':props['mesh_idx'][:,1]},
        'split_event_parent_event_id': {'dims':dims, 'data':props['event_id']},
    }
    return xr.Dataset.from_dict(d)

def split_group_dataset_from_props(props, centroid_names=('split_group_lon',
                                                          'split_group_lat')):
    """ props is the numpy array with named dtype returned by split_event_dataset """
    
    dims = ('number_of_split_group_children',)
    d ={
        centroid_names[0]: {'dims':dims, 'data':props['poly_ctr'][:,0]},
        centroid_names[1]: {'dims':dims, 'data':props['poly_ctr'][:,1]},
        'split_group_mesh_area_fraction': {'dims':dims, 'data':props['mesh_frac_area']},
        'split_group_area_fraction': {'dims':dims, 'data':props['event_frac_area']},
        'split_group_mesh_x_idx': {'dims':dims, 'data':props['mesh_idx'][:,0]},
        'split_group_mesh_y_idx': {'dims':dims, 'data':props['mesh_idx'][:,1]},
        'split_group_parent_group_id': {'dims':dims, 'data':props['event_id']},
    }
    return xr.Dataset.from_dict(d)

def split_flash_dataset_from_props(props, centroid_names=('split_flash_lon',
                                                          'split_flash_lat')):
    """ props is the numpy array with named dtype returned by split_event_dataset """
    
    dims = ('number_of_split_flash_children',)
    d ={
        centroid_names[0]: {'dims':dims, 'data':props['poly_ctr'][:,0]},
        centroid_names[1]: {'dims':dims, 'data':props['poly_ctr'][:,1]},
        'split_flash_mesh_area_fraction': {'dims':dims, 'data':props['mesh_frac_area']},
        'split_flash_area_fraction': {'dims':dims, 'data':props['event_frac_area']},
        'split_flash_mesh_x_idx': {'dims':dims, 'data':props['mesh_idx'][:,0]},
        'split_flash_mesh_y_idx': {'dims':dims, 'data':props['mesh_idx'][:,1]},
        'split_flash_parent_flash_id': {'dims':dims, 'data':props['event_id']},
    }
    return xr.Dataset.from_dict(d)

def replicate_and_weight_split_child_dataset(glm, split_child_dataset,
        parent_id='event_id', split_child_parent_id='split_event_parent_event_id',
        names=['event_energy', 'event_time_offset',
               'event_parent_flash_id', 'event_parent_group_id'],
        weights={'event_energy':'split_event_area_fraction'}):
    """
    Create a child level of the hierarchy that corresponds properties of its
    parent that have been geometrically split. Apply fractional weights.
        
    The default args/kwargs show how to split the GLM event dataset into a set
    of sub-event children. This function can also be used to split flashes
    given a set of flash-level polygons. Those polygons are assumed to have no
    overlap - i.e., the constituent events from that flash have been unioned
    and then split. In this way, we divide up flash-level properties without
    regard to the values of the lower-level children.
    """

    split_dims = getattr(split_child_dataset, split_child_parent_id).dims
    replicated_event_ids = getattr(split_child_dataset, split_child_parent_id)

    # it is important that this step keep the events in the same order
    # and retain the replication.
    glm_data = glm.reduce_to_entities(parent_id, replicated_event_ids)
    
    for name in names:
        new_name = 'split_' + name
        new_var = getattr(glm_data, name).data
        if name in weights:
            weight_var = getattr(split_child_dataset, weights[name])
            # dimension names won't match, but lengths should.
            new_var = new_var*weight_var.data # should ensure copy, not view
        # add variable to the dataset
        split_child_dataset[new_name] = (split_dims, new_var) #{'dims':split_dims, 'data':new_var}
        
    return split_child_dataset
