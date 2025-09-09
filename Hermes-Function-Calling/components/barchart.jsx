import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';

const BarChart = ({ data, xAxisKey, yAxisKey }) => {
  const d3Container = useRef(null);

  useEffect(() => {
    if (data && d3Container.current) {
      // Clear previous SVG
      d3.select(d3Container.current).selectAll('*').remove();

      
      const typedData = data.map(d => ({
        ...d,
        [yAxisKey]: +d[yAxisKey]
      }));

    
      const margin = { top: 20, right: 20, bottom: 40, left: 50 };
      const width = 500 - margin.left - margin.right;
      const height = 350 - margin.top - margin.bottom;

      const svg = d3.select(d3Container.current)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom);

      const g = svg.append('g')
        .attr('transform', `translate(${margin.left}, ${margin.top})`);

      const xScale = d3.scaleBand()
        .domain(typedData.map(d => d[xAxisKey]))
        .range([0, width])
        .padding(0.2);

      const yScale = d3.scaleLinear()
        .domain([0, d3.max(typedData, d => d[yAxisKey])])
        .range([height, 0]); 

      
      g.append('g')
        .attr('transform', `translate(0, ${height})`)
        .call(d3.axisBottom(xScale));

    
      g.append('g')
        .call(d3.axisLeft(yScale));

     
      g.selectAll('rect')
        .data(typedData)
        .join('rect')
        .attr('x', d => xScale(d[xAxisKey]))
        .attr('y', d => yScale(d[yAxisKey]))
        .attr('width', xScale.bandwidth())
        .attr('height', d => height - yScale(d[yAxisKey]))
        .attr('fill', 'steelblue');
    }
  }, [data, xAxisKey, yAxisKey]); 

  return (
    <div ref={d3Container} />
  );
};

export default BarChart;