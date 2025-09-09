import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import cloud from 'd3-cloud';

const WordCloud = ({ data }) => {
  const d3Container = useRef(null);

  useEffect(() => {
    if (data && d3Container.current) {
     
      d3.select(d3Container.current).selectAll('*').remove();

    
      const words = data
        .replace(/[^a-zA-Z\s]/g, '') 
        .toLowerCase()
        .split(/\s+/)
        .filter(word => word.length > 2); 

      const wordCounts = {};
      words.forEach(word => {
        wordCounts[word] = (wordCounts[word] || 0) + 1;
      });

      const wordEntries = Object.keys(wordCounts).map(key => ({
        text: key,
        size: 10 + wordCounts[key] * 5, 
      })).slice(0, 100); 

      
      const layout = cloud()
        .size([500, 500])
        .words(wordEntries)
        .padding(5)
        .rotate(() => (~~(Math.random() * 6) - 3) * 30) 
        .fontSize(d => d.size)
        .on('end', draw); 

      layout.start();

 
      function draw(words) {
        const svg = d3.select(d3Container.current)
          .append('svg')
          .attr('width', layout.size()[0])
          .attr('height', layout.size()[1]);

        const g = svg.append('g')
          .attr('transform', `translate(${layout.size()[0] / 2},${layout.size()[1] / 2})`);

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        g.selectAll('text')
          .data(words)
          .join('text')
          .style('font-size', d => `${d.size}px`)
          .style('font-family', 'Impact')
          .style('fill', (d, i) => color(i))
          .attr('text-anchor', 'middle')
          .attr('transform', d => `translate(${d.x}, ${d.y})rotate(${d.rotate})`)
          .text(d => d.text);
      }
    }
  }, [data]); 

  return (
    <div ref={d3Container} style={{ width: '500px', height: '500px', margin: 'auto' }} />
  );
};

export default WordCloud;