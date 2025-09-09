import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';

const PieChart = ({ data, categoryKey, valueKey }) => {
  const d3Container = useRef(null);

  useEffect(() => {
    if (data && d3Container.current) {
      d3.select(d3Container.current).selectAll('*').remove();
      
      const typedData = data.map(d => ({
        ...d,
        [valueKey]: +d[valueKey]
      }));

     
      const width = 450;
      const height = 450;
      const radius = Math.min(width, height) / 2;

      const svg = d3.select(d3Container.current)
        .append('svg')
          .attr('width', width)
          .attr('height', height)
        .append('g')
          .attr('transform', `translate(${width / 2}, ${height / 2})`);

      const color = d3.scaleOrdinal(d3.schemeTableau10)
        .domain(typedData.map(d => d[categoryKey]));

      const pie = d3.pie()
        .value(d => d[valueKey])
        .sort(null);

      const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius * 0.8);
        
      const outerArc = d3.arc()
        .innerRadius(radius * 0.9)
        .outerRadius(radius * 0.9);

   
      svg.selectAll('path')
        .data(pie(typedData))
        .join('path')
        .attr('d', arc)
        .attr('fill', d => color(d.data[categoryKey]))
        .attr('stroke', 'white')
        .style('stroke-width', '2px');
        
     
      svg.selectAll('allPolylines')
        .data(pie(typedData))
        .join('polyline')
          .attr('stroke', 'black')
          .style('fill', 'none')
          .attr('stroke-width', 1)
          .attr('points', d => {
              const posA = arc.centroid(d);
              const posB = outerArc.centroid(d);
              const posC = outerArc.centroid(d);
              posC[0] = radius * 0.95 * (midAngle(d) < Math.PI ? 1 : -1);
              return [posA, posB, posC];
          });
          
      function midAngle(d) { return d.startAngle + (d.endAngle - d.startAngle) / 2; }
      
      svg.selectAll('allLabels')
        .data(pie(typedData))
        .join('text')
          .text(d => d.data[categoryKey])
          .attr('transform', d => {
              const pos = outerArc.centroid(d);
              pos[0] = radius * (midAngle(d) < Math.PI ? 1 : -1);
              return `translate(${pos})`;
          })
          .style('text-anchor', d => (midAngle(d) < Math.PI ? 'start' : 'end'));
    }
  }, [data, categoryKey, valueKey]);

  return <div ref={d3Container} />;
};

export default PieChart;