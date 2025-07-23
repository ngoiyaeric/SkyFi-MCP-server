# Area of Interest (AOI) Guide

This guide explains the format requirements, limitations, and tools for working with Areas of Interest in the SkyFi Platform API.

## AOI Format

All AOI fields are expected to be a simple convex POLYGON in the WKT (Well-Known Text) format.

### Example Format
```
POLYGON ((-97.672442134274 30.289674402322873, -97.67245401025714 30.244570392925723, -97.72440367372722 30.244570392925723, -97.72441554971037 30.289674402322873, -97.672442134274 30.289674402322873))
```

**Important**: The first and last coordinate pairs must be identical to close the polygon.

## AOI Limits

Different operations have different AOI constraints:

### Orders
- Maximum vertices: **500**
- No area limit

### Archive Searches
- Maximum vertices: **500**
- Maximum area: **500,000 sq km**

### Notifications
- Maximum vertices: **500**
- Maximum area: **500,000 sq km**

## Tools and Calculators

### 1. Calculate AOI Size in Square Kilometers

SkyFi provides a Python notebook to help calculate the size of your AOI in square kilometers. This calculation is essential for:
- Determining order cost
- Ensuring compliance with AOI constraints
- Verifying minimum and maximum area requirements

**[Access the AOI Size Calculator Notebook](https://colab.research.google.com/drive/1example)**

#### How to Use:
1. Open the notebook using the link above
2. Create a copy in your personal Google Drive or preferred environment
3. Update the polygon with your specific AOI coordinates
4. Run the cell to calculate the area in square kilometers

**Note**: The notebook calculates size only, not cost. For cost information, refer to the [pricing guidelines](https://skyfi.com/pricing).

### 2. Generate AOI from Center Point

If you need to create a polygonal AOI given a center point and desired area, use this tool:

**[Access the AOI Generator Notebook](https://colab.research.google.com/drive/1example)**

#### How to Use:
1. Open the notebook by clicking the link above
2. Make a copy to your personal environment
3. Change the values of:
   - Center point coordinates (latitude, longitude)
   - Desired area in square kilometers
4. Execute the notebook cells in order
5. Retrieve the generated AOI polygon from the output

The generated polygon coordinates can be used directly in API requests to order satellite imagery for your specific area.

## Best Practices

1. **Validate Polygon Closure**: Always ensure your polygon is closed (first point equals last point)
2. **Check Vertex Count**: Count vertices before submitting to avoid exceeding the 500-vertex limit
3. **Verify Area Constraints**: For searches and notifications, calculate area to ensure it's under 500,000 sq km
4. **Use Simple Polygons**: Avoid self-intersecting polygons or polygons with holes
5. **Coordinate Order**: Use longitude first, then latitude (following WKT standard)

## Common Issues

### Invalid Polygon Errors
- Ensure polygon is closed
- Check for self-intersections
- Verify coordinate order (longitude, latitude)

### Area Constraint Violations
- Calculate area before submission
- Consider breaking large areas into multiple smaller requests

### Vertex Limit Exceeded
- Simplify complex polygons
- Use polygon simplification algorithms if needed

## Support

For assistance with AOI-related issues or questions, contact api@skyfi.com. Include your AOI polygon and any error messages for faster resolution.