/**
 * world.ts — real pictures of the ad's world, found in open collections
 * (taste-skill assets.mjs) and credited on the page. They show the monsoon
 * city around the product; none is presented as the product itself.
 * Sources and licences: public/assets/world/credits.json.
 */

export interface WorldPicture {
  src: string;
  width: number;
  height: number;
  alt: string;
  credit: string;
}

export const MONSOON_SKYLINE: WorldPicture = {
  src: '/assets/world/mumbai-monsoon-skyline.jpg',
  width: 1024,
  height: 650,
  alt: 'Monsoon clouds rolling low over the Mumbai skyline',
  credit: '“And it Rains in Mumbai!!” by AbhijeetRane, CC BY 2.0, via Flickr',
};

export const MUMBAI_TAXIS: WorldPicture = {
  src: '/assets/world/mumbai-taxis.jpg',
  width: 1600,
  height: 1066,
  alt: 'A line of black-and-yellow Mumbai taxis waiting on a palm-lined road',
  credit: '“Mumbai, India, Mumbai taxi (taxicab) on the road” by Vyacheslav Argenberg, CC BY 4.0, via Wikimedia Commons',
};

export const BANGALORE_STREET: WorldPicture = {
  src: '/assets/world/bangalore-commercial-street.jpg',
  width: 1200,
  height: 750,
  alt: 'A painted vintage postcard of Commercial Street, Bangalore',
  credit: '“Street-bangalore-2” by Paper Jewels, CC BY 4.0, via Wikimedia Commons',
};

export const WORLD_CREDITS = [MONSOON_SKYLINE, MUMBAI_TAXIS, BANGALORE_STREET].map((p) => p.credit);
